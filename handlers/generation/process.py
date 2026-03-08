# handlers/generation/process.py

import asyncio
import base64
import aiohttp
import os
import re
import tempfile
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.models import User, Generation, GenerationStatus, MessageHistory
from services.api_client import APIClient
from keyboards.inline import main_menu, back_to_menu_kb
from utils.logger import logger
from model_config import MODEL_CATALOG
from states.generation_states import GenState
from services.fal_ai import upload_file_to_fal


router = Router(name="process_router")


ALL_MODELS = {}
for category, families in MODEL_CATALOG.items():
    for family_key, family_data in families.items():
        for model in family_data["models"]:
            ALL_MODELS[model["id"]] = model


_MD_LINK_RE = re.compile(r"^\s*\[[^\]]+\]\((https?://[^)\s]+)\)\s*$")
_URL_RE = re.compile(r"(https?://[^\s\])>\"']+)")


def normalize_url(raw: Optional[str]) -> Optional[str]:
    """
    Приводит строку к «чистому» URL.
    Поддерживает случаи, когда URL пришёл в Markdown-виде: [text](https://...)
    """
    if not raw:
        return None

    s = str(raw).strip()

    m = _MD_LINK_RE.match(s)
    if m:
        url = m.group(1)
    else:
        m2 = _URL_RE.search(s)
        if m2:
            url = m2.group(1)
        else:
            url = s

    # Дополнительная очистка URL от недопустимых символов
    # Telegram не принимает URL с пробелами и некоторыми спецсимволами
    url = url.replace(" ", "%20")
    url = url.replace("{", "%7B").replace("}", "%7D")
    url = url.replace("|", "%7C")
    url = url.replace("\\", "/")
    url = url.replace("^", "%5E")
    url = url.replace("`", "%60")

    return url


@router.message(GenState.waiting_for_first_image, F.photo)
async def step_first_image(message: Message, state: FSMContext, session: AsyncSession):
    photo = message.photo[-1]
    file_id = photo.file_id

    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    model_id = user.current_model

    await state.update_data(first_image_file_id=file_id)

    if "motion-control" in model_id:
        await message.answer(
            "2️⃣ <b>Шаг 2:</b> Отлично! Теперь отправьте <b>видео</b> (референс движения).",
            parse_mode="HTML",
        )
        await state.set_state(GenState.waiting_for_reference_video)
    elif "first-last" in model_id:
        await message.answer(
            "2️⃣ <b>Шаг 2:</b> Принято! Теперь отправьте <b>второе изображение</b> (конечный кадр).",
            parse_mode="HTML",
        )
        await state.set_state(GenState.waiting_for_second_image)
    else:
        await message.answer("📸 Фото принято. Добавьте описание (промпт) или нажмите кнопку.", reply_markup=back_to_menu_kb())
        await state.set_state(GenState.waiting_for_input)


@router.message(GenState.waiting_for_reference_video, F.video)
async def step_reference_video(message: Message, state: FSMContext, session: AsyncSession):
    video = message.video
    logger.info(
        f"step_reference_video: получено видео, file_id={video.file_id}, размер={video.file_size / (1024*1024):.2f}MB"
    )

    if video.file_size > 50 * 1024 * 1024:
        await message.answer("❌ Видео слишком большое! Пожалуйста, до 50 МБ.")
        return

    data = await state.get_data()
    first_image_file_id = data.get("first_image_file_id")

    if not first_image_file_id:
        await message.answer("❌ Ошибка: потеряно первое изображение. Начните заново.")
        await state.clear()
        return

    prompt = message.caption or "An african american woman dancing"
    await state.update_data(prompt=prompt)

    logger.info(
        f"step_reference_video: запускаем complex_generation, first_image={first_image_file_id}, "
        f"video={video.file_id}, prompt='{prompt}'"
    )

    await run_complex_generation(message, session, first_image_file_id, video_file_id=video.file_id, prompt=prompt)
    await state.clear()


@router.message(GenState.waiting_for_second_image, F.photo)
async def step_second_image(message: Message, state: FSMContext, session: AsyncSession):
    photo = message.photo[-1]
    data = await state.get_data()
    first_image_file_id = data.get("first_image_file_id")

    if not first_image_file_id:
        await message.answer("❌ Ошибка: потеряно первое изображение. Начните заново.")
        await state.clear()
        return

    prompt = message.caption
    await run_complex_generation(message, session, first_image_file_id, second_image_file_id=photo.file_id, prompt=prompt)
    await state.clear()


@router.message((F.text) | (F.photo) | (F.video))
async def handle_standard_input(message: Message, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()

    # Если уже идет генерация — игнорируем повторные сообщения (защита от "альбомов")
    if current_state == GenState.generating:
        logger.info(f"handle_standard_input: генерация уже идет, игнорируем сообщение от {message.from_user.id}")
        return
    
    if current_state and current_state != GenState.waiting_for_input:
        logger.info(f"handle_standard_input: в состоянии {current_state}, тип={type(message).__name__}, игнорируем")
        return

    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return

    model_id = user.current_model
    if model_id not in ALL_MODELS:
        model_id = "openai/gpt-4o-mini"

    model_info = ALL_MODELS[model_id]
    category = model_info.get("category", "gen_text")
    if "category" not in model_info:
        for cat, families in MODEL_CATALOG.items():
            for fam_data in families.values():
                for m in fam_data["models"]:
                    if m["id"] == model_id:
                        category = cat
                        break

    # Проверка: текстовые модели должны принимать только текст
    if category in ["gen_text", "gen_search"]:
        if not message.text:
            await message.answer("⚠️ <b>Текстовая модель ожидает текст!</b>\n\nПожалуйста, отправьте ваш запрос текстом.", parse_mode="HTML")
            return

    # Проверка: image-to-video модели требуют фото
    is_img_model = "image-to" in model_id or "img2vid" in model_info["name"].lower()
    if category == "gen_video" and is_img_model and not message.photo:
        await message.answer("❌ Эта модель требует <b>фотографию</b>! Прикрепите изображение.", parse_mode="HTML")
        return

    # Для изображений — обрабатываем фото и/или текст
    if category in ["gen_image", "gen_nano_banana"]:
        # Ставим состояние "генерация идет" для блокировки повторных запросов
        await state.set_state(GenState.generating)

        # Собираем референсы из фото (до 3)
        reference_images = []

        # Проверяем, есть ли медиа-группа (альбом)
        media_group_id = message.media_group_id

        if media_group_id:
            # Это часть альбома — сохраняем в state и ждем остальные фото
            data = await state.get_data()
            # Исправление: используем or [] вместо , [] для защиты от None
            album_photos = data.get("album_photos") or []
            album_prompt = data.get("album_prompt") or ""

            logger.info(f"Album processing: получено фото в альбоме, всего собрано: {len(album_photos) + 1}")

            # Добавляем текущее фото
            photo = message.photo[-1]
            ref_url = await _get_file_url_or_base64(message.bot, photo.file_id)
            if ref_url:
                album_photos.append(ref_url)

            # Сохраняем caption (промпт) — берем из первого сообщения с текстом
            if message.caption and not album_prompt:
                album_prompt = message.caption
                logger.info(f"Album processing: промпт из caption: {album_prompt[:50]}...")

            # Сохраняем данные в state
            await state.update_data(album_photos=album_photos, album_prompt=album_prompt)

            # Если это первое сообщение альбома — ждем остальные
            if len(album_photos) == 1:
                # Первое фото — ждем 1 секунду на случай получения остальных
                logger.info("Album processing: первое фото, ждем остальные 1.0 сек...")
                await asyncio.sleep(1.0)
                data = await state.get_data()
                album_photos = data.get("album_photos") or []

            # Если фото еще приходят — ждем
            if len(album_photos) < 4:  # Максимум 3 фото + 1 проверка
                # Проверяем, пришли ли еще фото за последнюю секунду
                logger.info(f"Album processing: собрано {len(album_photos)} фото, ждем еще 0.5 сек...")
                await asyncio.sleep(0.5)
                data = await state.get_data()
                album_photos = data.get("album_photos") or []

            # НЕ очищаем state здесь — очистка будет в run_image_generation
            logger.info(f"Album processing: финальное количество фото: {len(album_photos)}")

            # Используем собранные фото альбома как референсы
            reference_images = album_photos[:3]  # Максимум 3 референса
            prompt = album_prompt or ""
        else:
            # Одиночное фото (не альбом)
            if message.photo:
                photo = message.photo[-1]
                ref_url = await _get_file_url_or_base64(message.bot, photo.file_id)
                if ref_url:
                    reference_images.append(ref_url)

            # Получаем промпт из текста или caption к фото
            prompt = message.text or message.caption or ""

        # Если нет ни фото ни текста — просим ввести что-то
        if not reference_images and not prompt:
            await state.set_state(GenState.waiting_for_input)
            await message.answer(
                "⚠️ <b>Отправьте текст и/или фото!</b>\n\n"
                "Для генерации изображения нужен хотя бы один из параметров:\n"
                "• Текстовый промпт (описание)\n"
                "• 1-3 фотографии как референсы",
                parse_mode="HTML"
            )
            return

        # Запускаем генерацию
        await run_image_generation(message, session, prompt, reference_images, state)
        return

    await run_simple_generation(message, user, session, model_info, category)


async def run_complex_generation(
    message: Message,
    session: AsyncSession,
    first_file_id: str,
    video_file_id: str = None,
    second_image_file_id: str = None,
    prompt: str = None,
):
    """
    Сложная генерация видео (Motion Control, First-Last Frame).
    Использует видео-пакеты вместо токенов.
    """
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()

    model_id = user.current_model
    model_info = ALL_MODELS.get(model_id, {"cost": 0, "name": "Unknown"})
    cost = model_info.get("cost", 0)

    # Проверяем баланс видео-генераций (1 генерация = 1 видео)
    if user.video_generations_balance < 1:
        await message.answer(
            "❌ <b>Недостаточно видео-генераций!</b>\n\n"
            "Приобретите пакет видео-генераций в разделе 💎 Подписка.",
            parse_mode="HTML"
        )
        return

    # Списываем 1 видео-генерацию
    user.video_generations_balance -= 1
    await session.commit()

    status_msg = await message.answer(
        f"⏳ <b>{model_info['name']}</b>\nЗагружаю файлы и колдую...\n\n"
        f"⏱️ Генерация может занять <b>7-10 минут</b>. Пожалуйста, подождите...",
        parse_mode="HTML",
    )
    api = APIClient()

    tmp_path = None

    try:
        logger.info(f"Complex Gen: model={model_id}, video={video_file_id}, prompt={prompt}")

        first_url = await _get_file_url_or_base64(message.bot, first_file_id, is_video=False)
        if not first_url:
            raise Exception("Не удалось загрузить первое изображение")

        second_url = None
        video_url = None

        if second_image_file_id:
            second_url = await _get_file_url_or_base64(message.bot, second_image_file_id, is_video=False)
            if not second_url:
                raise Exception("Не удалось загрузить второе изображение")

        if video_file_id:
            video_url = await _get_file_url_or_base64(message.bot, video_file_id, is_video=True)
            if not video_url:
                raise Exception("Не удалось получить ссылку на видео")

        logger.info(f"Complex Gen: URLs obtained. Video: {bool(video_url)}")

        if not prompt:
            prompt = message.caption or message.text or "Masterpiece"

        extra = {}
        if second_url:
            extra["second_image_url"] = second_url
        if video_url:
            extra["video_url"] = video_url

        logger.info("Complex Gen: вызов api.generate_video")
        res_url_raw = await api.generate_video(model_id, prompt, image_url=first_url, extra_params=extra)

        if not res_url_raw:
            raise Exception("Генерация не вернула результат (ошибка FAL AI)")

        res_url = normalize_url(res_url_raw)
        if not res_url:
            raise Exception("Не удалось извлечь URL результата")

        logger.info(f"Complex Gen: Результат готов: {res_url}. Пытаемся отправить как VIDEO по URL...")

        # --- НОВАЯ ЛОГИКА: Скачиваем всегда, если можем, чтобы отправить и видео, и файл ---
        logger.info("Complex Gen: Скачиваем видео локально для отправки...")
        tmp_path = await download_to_tempfile(res_url)

        sent_video_ok = False

        # 1. Отправляем как ВИДЕО (красиво, для просмотра)
        if tmp_path and os.path.exists(tmp_path):
            try:
                # Отправляем скачанный файл как видео
                input_file_video = FSInputFile(tmp_path, filename="video.mp4")
                await message.answer_video(
                    input_file_video,
                    caption=f"🎬 <b>{model_info['name']}</b>\n🎬 -1 генерация",
                    parse_mode="HTML",
                    reply_markup=back_to_menu_kb(),
                    supports_streaming=True
                )
                sent_video_ok = True
                logger.info("Complex Gen: Видео (upload) отправлено успешно.")
            except Exception as e:
                logger.warning(f"Complex Gen: Ошибка отправки видео-файлом: {e}")

        if not sent_video_ok:
            # Если скачать не удалось или не отправилось файлом - пробуем URL (старый метод)
            try:
                await message.answer_video(
                    res_url,
                    caption=f"🎬 <b>{model_info['name']}</b>\n🎬 -1 генерация",
                    parse_mode="HTML",
                    reply_markup=back_to_menu_kb(),
                )
                sent_video_ok = True
                logger.info("Complex Gen: Видео отправлено по URL (Telegram fetch).")
            except Exception as e:
                logger.warning(f"Complex Gen: Ошибка отправки по URL: {e}")

        # 2. Отправляем как ДОКУМЕНТ (для сохранения качества), если файл скачался
        if tmp_path and os.path.exists(tmp_path) and sent_video_ok:
            try:
                input_file_doc = FSInputFile(tmp_path, filename="video_source.mp4")
                await message.answer_document(
                    input_file_doc,
                    caption="📂 <b>Исходный файл</b> (без сжатия)",
                    parse_mode="HTML"
                )
                logger.info("Complex Gen: Документ-исходник отправлен.")
            except Exception as e:
                logger.warning(f"Complex Gen: Ошибка отправки документа: {e}")

        # Если вообще ничего не отправилось
        if not sent_video_ok:
             await message.answer(
                f"✅ <b>Видео готово!</b>\n\n"
                f"🎬 Модель: <b>{model_info['name']}</b>\n"
                f"🎬 -1 генерация\n\n"
                f"⚠️ Не удалось загрузить видео в Telegram, вот прямая ссылка:\n"
                f"🔗 <a href='{res_url}'>Скачать видео</a>",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb(),
            )

        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
        except:
            pass

        session.add(
            Generation(
                user_id=user.id,
                model_name=model_id,
                prompt=prompt,
                result="OK",
                status=GenerationStatus.COMPLETED,
                cost=1,  # 1 видео-генерация
            )
        )
        await session.commit()

    except Exception as e:
        logger.error(f"Complex Gen Error: {e}")
        # Возвращаем видео-генерацию при ошибке
        user.video_generations_balance += 1
        await session.commit()
        try:
            await status_msg.edit_text(f"❌ Ошибка: {str(e)}")
        except:
            await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        # Удаляем временный файл
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass


async def run_image_generation(
    message: Message,
    session: AsyncSession,
    prompt: str,
    reference_images: list = None,
    state: FSMContext = None,
):
    """
    Генерация изображения с поддержкой референсов.

    Args:
        message: Сообщение с промптом
        session: DB сессия
        prompt: Текстовый промпт
        reference_images: Список URL/base64 референсов (до 3)
        state: FSM state для сброса после генерации
    """
    if reference_images is None:
        reference_images = []

    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()

    model_id = user.current_model
    model_info = ALL_MODELS.get(model_id, {"cost": 1, "name": "Unknown"})
    cost = model_info.get("cost", 1)

    if user.tokens_balance < cost:
        if state:
            await state.set_state(GenState.waiting_for_input)
        await message.answer(f"❌ Недостаточно токенов! Нужно {cost}.", parse_mode="HTML")
        return

    user.tokens_balance -= cost
    await session.commit()

    status_msg = await message.answer(
        f"⏳ <b>{model_info['name']}</b>\nГенерирую изображение...",
        parse_mode="HTML"
    )

    api = APIClient()

    try:
        # Вызываем генератор с референсами
        res = await api.generate_image(model_info["id"], prompt, reference_images=reference_images)

        if not res:
            raise Exception("Ошибка генерации изображения")

        await status_msg.delete()

        # Проверяем тип результата: URL (строка) или BufferedInputFile (файл)
        from aiogram.types import BufferedInputFile

        try:
            if isinstance(res, BufferedInputFile):
                # Изображение в base64 — отправляем как файл
                logger.info("Sending image as BufferedInputFile (base64)")
                await message.answer_photo(
                    res,
                    caption=f"🎨 <b>{model_info['name']}</b>\n🍌 -{cost}",
                    parse_mode="HTML",
                    reply_markup=back_to_menu_kb(),
                )
            else:
                # Изображение по URL
                image_url = normalize_url(str(res))
                logger.info(f"Image URL: {image_url}")
                await message.answer_photo(
                    image_url,
                    caption=f"🎨 <b>{model_info['name']}</b>\n🍌 -{cost}",
                    parse_mode="HTML",
                    reply_markup=back_to_menu_kb(),
                )
        except Exception as send_error:
            # Если отправка не удалась — пробуем показать ссылку
            logger.error(f"Failed to send image: {send_error}")
            if not isinstance(res, BufferedInputFile):
                image_url = normalize_url(str(res))
                await message.answer(
                    f"🎨 <b>{model_info['name']}</b>\n"
                    f"🍌 -{cost}\n\n"
                    f"⚠️ Не удалось отправить изображение в Telegram.\n"
                    f"🔗 <a href='{image_url}'>Скачать изображение</a>",
                    parse_mode="HTML",
                    reply_markup=back_to_menu_kb(),
                )
            else:
                await message.answer(
                    f"🎨 <b>{model_info['name']}</b>\n"
                    f"🍌 -{cost}\n\n"
                    f"⚠️ Ошибка отправки: {send_error}",
                    parse_mode="HTML",
                    reply_markup=back_to_menu_kb(),
                )

        session.add(
            Generation(
                user_id=user.id,
                model_name=model_id,
                prompt=prompt,
                result="OK",
                status=GenerationStatus.COMPLETED,
                cost=cost,
            )
        )
        await session.commit()

    except Exception as e:
        logger.error(f"Image Gen Error: {e}")
        user.tokens_balance += cost
        await session.commit()
        try:
            await status_msg.edit_text(f"❌ Ошибка: {str(e)}", reply_markup=back_to_menu_kb())
        except:
            await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=back_to_menu_kb())
    finally:
        # Очищаем state от временных данных альбома (если использовался)
        if state:
            await state.update_data(album_photos=None, album_prompt=None)
            await state.set_state(GenState.waiting_for_input)


async def run_simple_generation(message: Message, user: User, session: AsyncSession, model_info: dict, category: str):
    cost = model_info.get("cost", 1)
    prompt = message.caption or message.text or ""

    # Для видео используем отдельный баланс видео-генераций
    if category == "gen_video":
        if user.video_generations_balance < 1:
            await message.answer(
                "❌ <b>Недостаточно видео-генераций!</b>\n\n"
                "Приобретите пакет видео-генераций в разделе 💎 Подписка.",
                parse_mode="HTML"
            )
            return
        
        # Списываем 1 видео-генерацию
        user.video_generations_balance -= 1
    else:
        # Для остальных категорий (текст, изображения, поиск) используем токены
        if user.tokens_balance < cost:
            await message.answer(f"❌ Недостаточно токенов! Нужно {cost}.", parse_mode="HTML")
            return
        
        # Списываем токены
        user.tokens_balance -= cost
    
    await session.commit()

    status_msg = await message.answer(f"⏳ <b>{model_info['name']}</b>\nДумаю...", parse_mode="HTML")
    api = APIClient()

    try:
        image_url = None
        if message.photo:
            image_url = await _get_file_url_or_base64(message.bot, message.photo[-1].file_id)
            if not prompt:
                prompt = "Creative video"

        if category == "gen_video":
            res = await api.generate_video(model_info["id"], prompt, image_url=image_url)
            if not res:
                raise Exception("Ошибка видео")

            await status_msg.delete()
            await message.answer_video(
                normalize_url(res),
                caption=f"🎬 <b>{model_info['name']}</b>\n🎬 -1 генерация",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb(),
            )

        elif category == "gen_image":
            # Используем новую функцию с поддержкой референсов
            # Для обратной совместимости, если нет референсов - передаем пустой список
            await run_image_generation(message, session, prompt, reference_images=[])
            return  # run_image_generation уже сохраняет Generation и делает коммит

        elif category in ["gen_text", "gen_search"]:
            # Для текстовых моделей используем историю сообщений
            messages = [{"role": "user", "content": prompt}]
            res = await api.generate_text(
                model_info["id"],
                messages,
                session=session,
                user_id=user.id
            )
            await status_msg.delete()

            if res and not res.startswith("Error:"):
                # Успешная генерация — сохраняем историю (коммит будет ниже)
                session.add(
                    Generation(
                        user_id=user.id,
                        model_name=model_info["id"],
                        prompt=prompt,
                        result="OK",
                        status=GenerationStatus.COMPLETED,
                        cost=cost,
                    )
                )
                await message.answer(res[:4000], parse_mode="Markdown", reply_markup=back_to_menu_kb())
            else:
                # Ошибка генерации — откатываем токен и выходим
                user.tokens_balance += cost
                await session.commit()
                error_msg = res if res else "❌ Ошибка: не удалось получить ответ от модели"
                await message.answer(f"❌ {error_msg}", reply_markup=back_to_menu_kb())
                return  # Выходим, чтобы не дублировать коммит и сохранение Generation ниже

        # Для всех категорий (кроме ошибки текстовой модели) сохраняем генерацию
        session.add(
            Generation(
                user_id=user.id,
                model_name=model_info["id"],
                prompt=prompt,
                result="OK",
                status=GenerationStatus.COMPLETED,
                cost=cost,
            )
        )
        await session.commit()

    except Exception as e:
        logger.error(f"Simple Gen Error: {e}")
        # Возвращаем ресурсы при ошибке
        if category == "gen_video":
            user.video_generations_balance += 1
        else:
            user.tokens_balance += cost
        await session.commit()
        # Пробуем редактировать статусное сообщение, но если не выйдет — шлём новое
        try:
            await status_msg.edit_text(f"❌ Ошибка: {str(e)}", reply_markup=back_to_menu_kb())
        except:
            await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=back_to_menu_kb())


async def _get_file_url_or_base64(bot, file_id, is_video=False):
    logger.info(f"_get_file_url_or_base64: file_id={file_id}, is_video={is_video}")

    file = await bot.get_file(file_id)

    if is_video:
        telegram_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
        safe_url = telegram_url.replace(bot.token, "***")
        logger.info(f"Video URL (no download): {safe_url}")
        return telegram_url

    file_bytes_io = await bot.download_file(file.file_path)
    file_bytes = file_bytes_io.read()
    mime = "image/jpeg"
    file_size_mb = len(file_bytes) / (1024 * 1024)

    logger.info(f"Photo download: {file_size_mb:.2f}MB")

    try_upload = len(file_bytes) > 2 * 1024 * 1024
    if try_upload:
        filename = f"{file_id}.jpg"
        url = await upload_file_to_fal(file_bytes, filename, mime)
        if url:
            return url

    base64_str = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{base64_str}"


async def download_to_tempfile(url: str) -> Optional[str]:
    """
    Скачивает файл по URL в tmp (MAX STABILITY VERSION).
    """
    url = normalize_url(url)
    if not url:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # sock_read=None отключает таймаут на чтение пакетов, total=3600 дает час
    timeout = aiohttp.ClientTimeout(total=3600, sock_connect=60, sock_read=None)

    fd, path = tempfile.mkstemp(suffix=".mp4", prefix="nexusai_")
    os.close(fd)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"Downloading video (MAX STABILITY) from: {url}")
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"Download failed with status: {resp.status}")
                    return None

                with open(path, "wb") as f:
                    while True:
                        chunk = await resp.content.read(128 * 1024) # 128 KB chunks
                        if not chunk:
                            break
                        f.write(chunk)

        if os.path.exists(path) and os.path.getsize(path) > 0:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            logger.info(f"Video downloaded to tmp: {path}, size={size_mb:.2f} MB")
            return path
        else:
            logger.error("Download finished but file is empty or missing")
            return None

    except asyncio.TimeoutError:
        logger.error(f"Download timeout (MAX STABILITY) for: {url}")
        return None
    except Exception as e:
        logger.error(f"Error downloading content: {type(e).__name__}: {e}")
        return None
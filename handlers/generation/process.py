import asyncio
import base64
import aiohttp
import os
import re
import tempfile
from typing import Optional, Dict
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database.models import User, Generation, GenerationStatus, MessageHistory
from services.api_client import APIClient
from keyboards.inline import main_menu, back_to_menu_kb, post_generation_kb
from utils.logger import logger
from model_config import MODEL_CATALOG
from states.generation_states import GenState
from services.fal_ai import upload_file_to_fal

router = Router(name="process_router")

# Словари для сбора альбомов
_album_messages: Dict[str, list] = {}
_album_timers: Dict[str, asyncio.Task] = {}
_completed_albums: set = set()
ALBUM_WAIT_TIMEOUT = 2.5

ALL_MODELS = {}
for category, families in MODEL_CATALOG.items():
    for family_key, family_data in families.items():
        for model in family_data["models"]:
            ALL_MODELS[model["id"]] = {**model, "category": category}

MD_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^\s\)]+)\)")
URL_RE = re.compile(r"(https?://[^\s\)]+)")

def normalize_url(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = str(raw).strip()
    m = MD_LINK_RE.match(s)
    if m:
        url = m.group(1)
    else:
        m2 = URL_RE.search(s)
        if m2:
            url = m2.group(1)
        else:
            url = s

    url = url.replace(" ", "%20")
    url = url.replace("{", "%7B").replace("}", "%7D")
    url = url.replace("\\", "/")
    url = url.replace("\"", "%22")
    url = url.replace("`", "%60")
    return url

@router.message(GenState.waiting_for_first_image, F.photo)
async def step_first_image(message: Message, state: FSMContext, session: AsyncSession):
    photo = message.photo[-1]
    file_id = photo.file_id
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if not user: return
    model_id = user.current_model

    await state.update_data(first_image_file_id=file_id)

    if "motion-control" in model_id:
        await message.answer(
            "<b>Шаг 2:</b> Отлично! Теперь отправьте <b>видео</b> (референс движения).\n\n"
            "⚠️ <i>Максимальный размер видео — 20 МБ.</i>",
            parse_mode="HTML",
        )
        await state.set_state(GenState.waiting_for_reference_video)
    elif "first-last" in model_id:
        await message.answer(
            "<b>Шаг 2:</b> Принято! Теперь отправьте <b>второе изображение</b> (конечный кадр).",
            parse_mode="HTML",
        )
        await state.set_state(GenState.waiting_for_second_image)
    else:
        await message.answer("✅ Фото принято. Добавьте описание (промпт) или нажмите кнопку.", reply_markup=back_to_menu_kb())
        await state.set_state(GenState.waiting_for_input)

@router.message(GenState.waiting_for_reference_video, F.video)
async def step_reference_video(message: Message, state: FSMContext, session: AsyncSession):
    video = message.video
    logger.info(f"step_reference_video: получено видео, file_id={video.file_id}, размер {video.file_size / (1024*1024):.2f} MB")
    
    if video.file_size > 20*1024*1024:
        await message.answer("❌ Видео слишком большое! Telegram разрешает ботам скачивать файлы только до 20 MB. Пожалуйста, сожмите видео перед отправкой.")
        return

    data = await state.get_data()
    first_image_file_id = data.get("first_image_file_id")
    if not first_image_file_id:
        await message.answer("❌ Ошибка: потеряно первое изображение. Начните заново.")
        await state.clear()
        return

    prompt = message.caption or "A person performing an action from the reference video"
    await state.update_data(prompt=prompt)

    logger.info(f"step_reference_video: запускаем complex_generation, first_image={first_image_file_id}, video={video.file_id}, prompt={prompt}")
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
    logger.info(f"handle_standard_input ВЫЗВАН: text={bool(message.text)}, photo={bool(message.photo)}, video={bool(message.video)}, media_group_id={message.media_group_id}")
    media_group_id = message.media_group_id

    if media_group_id:
        if media_group_id in _completed_albums:
            return

        if media_group_id not in _album_messages:
            _album_messages[media_group_id] = []
        
        _album_messages[media_group_id].append(message)

        if media_group_id not in _album_timers:
            _album_timers[media_group_id] = asyncio.create_task(
                _process_album_task(message, state, session, media_group_id)
            )
    else:
        logger.info("Single message: обрабатываем как одиночное")
        return await _process_single_message(message, state, session)

async def _process_album_task(message: Message, state: FSMContext, session: AsyncSession, media_group_id: str):
    try:
        await asyncio.sleep(ALBUM_WAIT_TIMEOUT)
        
        _completed_albums.add(media_group_id)
        messages = _album_messages.pop(media_group_id, [])
        if media_group_id in _album_timers:
            del _album_timers[media_group_id]

        if not messages:
            return

        current_state = await state.get_state()
        if current_state and current_state not in [GenState.waiting_for_input, GenState.generating]:
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

        if category not in ["gen_image", "gen_nano_banana"]:
            logger.info(f"Album: не изображение (category={category}), игнорируем")
            return

        await state.set_state(GenState.generating)

        album_photos = []
        album_prompt = ""

        for msg in messages:
            if msg.photo:
                photo = msg.photo[-1]
                ref_url = await _get_file_url_or_base64(message.bot, photo.file_id)
                if ref_url:
                    album_photos.append(ref_url)
            
            if msg.caption and not album_prompt:
                album_prompt = msg.caption
            elif msg.text and not album_prompt:
                album_prompt = msg.text

        reference_images = album_photos[:3]
        prompt = album_prompt or ""

        data = await state.get_data()
        size_prompt = data.get("size_prompt", "")
        style_prompt = data.get("style_prompt", "")
        
        final_prompt = prompt
        if style_prompt:
            final_prompt += style_prompt
        if size_prompt:
            final_prompt += size_prompt

        logger.info(f"Album: запускаем генерацию с {len(reference_images)} референсами, prompt='{final_prompt[:30]}'")

        await state.set_state(GenState.waiting_for_input)
        await run_image_generation(message, session, final_prompt, reference_images, state)

    except Exception as e:
        logger.exception(f"Album task error: {e}")
        await state.set_state(GenState.waiting_for_input)
    finally:
        asyncio.create_task(cleanup_completed_album(media_group_id))

async def cleanup_completed_album(media_group_id: str):
    await asyncio.sleep(60)
    _completed_albums.discard(media_group_id)

async def _process_single_message(message: Message, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()
    if current_state == GenState.generating:
        logger.info(f"_process_single_message: генерация уже идет, игнорируем")
        return

    if current_state and current_state != GenState.waiting_for_input:
        logger.info(f"_process_single_message: в состоянии {current_state}, игнорируем")
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

    if category in ["gen_text", "gen_search"]:
        if not message.text:
            await message.answer("<b>Текстовая модель ожидает текст!</b>\nПожалуйста, отправьте ваш запрос текстом.", parse_mode="HTML")
            return

    is_img_model = "image-to" in model_id or "img2vid" in model_info["name"].lower()
    if category == "gen_video" and is_img_model and not message.photo:
        await message.answer("Эта модель требует <b>фотографию</b>! Прикрепите изображение.", parse_mode="HTML")
        return

    if category in ["gen_image", "gen_nano_banana"]:
        await state.set_state(GenState.generating)

        reference_images = []
        if message.photo:
            photo = message.photo[-1]
            ref_url = await _get_file_url_or_base64(message.bot, photo.file_id)
            if ref_url:
                reference_images.append(ref_url)
        
        prompt = message.text or message.caption or ""

        if not reference_images and not prompt:
            await state.set_state(GenState.waiting_for_input)
            await message.answer(
                "<b>Отправьте текст и/или фото!</b>\n\n"
                "Для генерации изображения нужен хотя бы один из параметров:\n"
                "• Текстовый промпт (описание)\n"
                "• 1-3 фотографии в качестве референсов",
                parse_mode="HTML"
            )
            return

        data = await state.get_data()
        size_prompt = data.get("size_prompt", "")
        style_prompt = data.get("style_prompt", "")
        
        final_prompt = prompt
        if style_prompt:
            final_prompt += style_prompt
        if size_prompt:
            final_prompt += size_prompt

        await run_image_generation(message, session, final_prompt, reference_images, state)
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
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()

    model_id = user.current_model
    model_info = ALL_MODELS.get(model_id, {"cost": 1, "name": "Unknown"})
    cost = model_info.get("cost", 1)

    if user.tokens_balance < cost:
        await message.answer(
            f"❌ <b>Недостаточно токенов!</b> Нужно {cost}.\n\n"
            "Приобретите пакет токенов в разделе Подписка.",
            parse_mode="HTML"
        )
        return

    user.tokens_balance -= cost
    await session.commit()

    status_msg = await message.answer(
        f"🎬 <b>{model_info['name']}</b>\nЗагружаю файлы и колдую...\n\n"
        "⏳ Генерация может занять <b>7-10 минут</b>. Пожалуйста, подождите...",
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

        res_url_raw = await api.generate_video(model_id, prompt, image_url=first_url, extra_params=extra)

        if not res_url_raw:
            raise Exception("Генерация не вернула результат (ошибка FAL AI)")

        res_url = normalize_url(res_url_raw)
        if not res_url:
            raise Exception("Не удалось извлечь URL результата")

        # СОХРАНЯЕМ В БД С ТЕМПОВЫМ РЕЗУЛЬТАТОМ
        gen = Generation(
            user_id=user.id,
            model_name=model_id,
            prompt=prompt,
            result="processing",
            status=GenerationStatus.COMPLETED,
            cost=cost,
        )
        session.add(gen)
        await session.commit()
        gen_id = gen.id

        tmp_path = await download_to_tempfile(res_url)
        sent_video_ok = False
        sent_msg = None

        if tmp_path and os.path.exists(tmp_path):
            try:
                input_file_video = FSInputFile(tmp_path, filename="video.mp4")
                sent_msg = await message.answer_video(
                    input_file_video,
                    caption=f"🎬 <b>{model_info['name']}</b>\n💎 -{cost} токенов",
                    parse_mode="HTML",
                    reply_markup=post_generation_kb(gen_id),
                    supports_streaming=True
                )
                sent_video_ok = True
            except Exception as e:
                logger.warning(f"Complex Gen: Ошибка отправки видео-файлом: {e}")

        if not sent_video_ok:
            try:
                sent_msg = await message.answer_video(
                    res_url,
                    caption=f"🎬 <b>{model_info['name']}</b>\n💎 -{cost} токенов",
                    parse_mode="HTML",
                    reply_markup=post_generation_kb(gen_id),
                )
                sent_video_ok = True
            except Exception as e:
                logger.warning(f"Complex Gen: Ошибка отправки по URL: {e}")

        # ОБНОВЛЯЕМ БД TELEGRAM FILE_ID
        if sent_video_ok and sent_msg and sent_msg.video:
            gen.result = sent_msg.video.file_id
            await session.commit()
        else:
            gen.result = res_url
            await session.commit()

        if tmp_path and os.path.exists(tmp_path) and sent_video_ok:
            try:
                input_file_doc = FSInputFile(tmp_path, filename="video_source.mp4")
                await message.answer_document(
                    input_file_doc,
                    caption="📄 <b>Исходный файл</b> (без сжатия)",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Complex Gen: Ошибка отправки документа: {e}")

        if not sent_video_ok:
            await message.answer(
                "✅ <b>Видео готово!</b>\n\n"
                f"🤖 Модель: <b>{model_info['name']}</b>\n"
                f"💎 -{cost} токенов\n\n"
                "⚠️ Не удалось загрузить видео в Telegram, вот прямая ссылка:\n"
                f"<a href='{res_url}'>Скачать видео</a>",
                parse_mode="HTML",
                reply_markup=post_generation_kb(gen_id),
            )

        try:
            await status_msg.delete()
        except:
            pass

    except Exception as e:
        logger.error(f"Complex Gen Error: {e}")
        user.tokens_balance += cost
        await session.commit()
        try:
            await status_msg.edit_text(f"❌ Ошибка: {str(e)}")
        except:
            await message.answer(f"❌ Ошибка: {str(e)}")

    finally:
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
        f"🎨 <b>{model_info['name']}</b>\nГенерирую изображение...",
        parse_mode="HTML"
    )

    api = APIClient()

    try:
        res = await api.generate_image(model_info["id"], prompt, reference_images=reference_images)

        if not res:
            raise Exception("Ошибка генерации изображения")

        await status_msg.delete()

        # СОХРАНЯЕМ В БД С ТЕМПОВЫМ РЕЗУЛЬТАТОМ
        gen = Generation(
            user_id=user.id,
            model_name=model_id,
            prompt=prompt,
            result="processing",
            status=GenerationStatus.COMPLETED,
            cost=cost,
        )
        session.add(gen)
        await session.commit()
        gen_id = gen.id

        sent_msg = None
        try:
            if isinstance(res, BufferedInputFile):
                sent_msg = await message.answer_photo(
                    res,
                    caption=f"🎨 <b>{model_info['name']}</b>\n💎 -{cost} токенов",
                    parse_mode="HTML",
                    reply_markup=post_generation_kb(gen_id),
                )
            else:
                image_url = normalize_url(str(res))
                sent_msg = await message.answer_photo(
                    image_url,
                    caption=f"🎨 <b>{model_info['name']}</b>\n💎 -{cost} токенов",
                    parse_mode="HTML",
                    reply_markup=post_generation_kb(gen_id),
                )
                
            # ОБНОВЛЯЕМ БД TELEGRAM FILE_ID
            if sent_msg and sent_msg.photo:
                gen.result = sent_msg.photo[-1].file_id
                await session.commit()
                
        except Exception as send_error:
            logger.error(f"Failed to send image: {send_error}")
            if not isinstance(res, BufferedInputFile):
                image_url = normalize_url(str(res))
                gen.result = image_url
                await session.commit()
                
                await message.answer(
                    f"🎨 <b>{model_info['name']}</b>\n"
                    f"💎 -{cost} токенов\n\n"
                    "⚠️ Не удалось отправить изображение в Telegram.\n"
                    f"<a href='{image_url}'>Скачать изображение</a>",
                    parse_mode="HTML",
                    reply_markup=post_generation_kb(gen_id),
                )
            else:
                await message.answer(
                    f"🎨 <b>{model_info['name']}</b>\n"
                    f"💎 -{cost} токенов\n\n"
                    f"❌ Ошибка отправки: {send_error}",
                    parse_mode="HTML",
                    reply_markup=back_to_menu_kb(),
                )

    except Exception as e:
        logger.error(f"Image Gen Error: {e}")
        user.tokens_balance += cost
        await session.commit()
        try:
            await status_msg.edit_text(f"❌ Ошибка: {str(e)}", reply_markup=back_to_menu_kb())
        except:
            await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=back_to_menu_kb())

    finally:
        if state:
            await state.update_data(album_photos=None, album_prompt=None)
            await state.set_state(GenState.waiting_for_input)

async def run_simple_generation(message: Message, user: User, session: AsyncSession, model_info: dict, category: str):
    cost = model_info.get("cost", 1)
    prompt = message.caption or message.text or ""

    if user.tokens_balance < cost:
        await message.answer(f"❌ Недостаточно токенов! Нужно {cost}.", parse_mode="HTML")
        return
    user.tokens_balance -= cost

    await session.commit()

    status_msg = await message.answer(f"🧠 <b>{model_info['name']}</b>\nдумаю...", parse_mode="HTML")

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
            
            gen = Generation(user_id=user.id, model_name=model_info["id"], prompt=prompt, result="processing", status=GenerationStatus.COMPLETED, cost=cost)
            session.add(gen)
            await session.commit()
            
            sent_msg = await message.answer_video(
                normalize_url(res),
                caption=f"🎬 <b>{model_info['name']}</b>\n💎 -{cost} токенов",
                parse_mode="HTML",
                reply_markup=post_generation_kb(gen.id),
            )
            
            if sent_msg and sent_msg.video:
                gen.result = sent_msg.video.file_id
                await session.commit()
            else:
                gen.result = str(res)
                await session.commit()
                
        elif category == "gen_image":
            await run_image_generation(message, session, prompt, reference_images=[])
            return
        elif category in ["gen_text", "gen_search"]:
            messages = [{"role": "user", "content": prompt}]
            res = await api.generate_text(
                model_info["id"],
                messages,
                session=session,
                user_id=user.id
            )
            
            await status_msg.delete()

            if res and not res.startswith("Error:"):
                gen = Generation(user_id=user.id, model_name=model_info["id"], prompt=prompt, result="OK", status=GenerationStatus.COMPLETED, cost=cost)
                session.add(gen)
                await session.commit()
                
                await message.answer(res[:4000], parse_mode="Markdown", reply_markup=post_generation_kb(gen.id))
            else:
                user.tokens_balance += cost
                await session.commit()
                error_msg = res if res else "Ошибка: не удалось получить ответ от модели"
                await message.answer(f"❌ {error_msg}", reply_markup=back_to_menu_kb())
                return

    except Exception as e:
        logger.error(f"Simple Gen Error: {e}")
        user.tokens_balance += cost
        await session.commit()
        
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
        logger.info(f"Video URL: {safe_url}. Downloading and uploading to FAL Storage...")
        
        try:
            file_bytes_io = await bot.download_file(file.file_path)
            file_bytes = file_bytes_io.read()
            mime = "video/mp4"
            filename = f"{file_id}.mp4"
            
            url = await upload_file_to_fal(file_bytes, filename, mime)
            if url:
                logger.info(f"Video successfully uploaded to FAL Storage: {url}")
                return url
            else:
                logger.warning("Failed to upload video to FAL Storage, falling back to Telegram URL")
        except Exception as e:
            logger.error(f"Error downloading/uploading video to FAL: {e}")
            
        return telegram_url

    file_bytes_io = await bot.download_file(file.file_path)
    file_bytes = file_bytes_io.read()
    mime = "image/jpeg"

    file_size_mb = len(file_bytes) / (1024*1024)
    logger.info(f"Photo download: {file_size_mb:.2f} MB")

    try_upload = len(file_bytes) > 2*1024*1024
    if try_upload:
        filename = f"{file_id}.jpg"
        url = await upload_file_to_fal(file_bytes, filename, mime)
        if url:
            return url

    base64_str = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{base64_str}"

async def download_to_tempfile(url: str) -> Optional[str]:
    url = normalize_url(url)
    if not url:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
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
                        chunk = await resp.content.read(128 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)

                if os.path.exists(path) and os.path.getsize(path) > 0:
                    size_mb = os.path.getsize(path) / (1024*1024)
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
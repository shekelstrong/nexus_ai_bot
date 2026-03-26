import os
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, Generation
from keyboards.inline import try_prompt_kb, back_to_menu_kb
from states.generation_states import GenState
from handlers.generation.process import run_image_generation, run_simple_generation
from model_config import MODEL_CATALOG
from utils.logger import logger

router = Router(name="share_router")

# ID твоего канала
CHANNEL_ID = -1003788406828

@router.callback_query(F.data.startswith("share_gen:"))
async def share_generation_cb(cb: CallbackQuery, session: AsyncSession):
    gen_id = int(cb.data.split(":")[1])
    res = await session.execute(select(Generation).where(Generation.id == gen_id))
    gen = res.scalar_one_or_none()

    if not gen:
        await cb.answer("❌ Генерация не найдена", show_alert=True)
        return

    # Защита: если URL картинки не сохранился (например, base64)
    if not gen.result or gen.result in ["OK", "OK (Base64)"]:
        await cb.answer("❌ Эту генерацию нельзя опубликовать (отсутствует прямая ссылка на медиа).", show_alert=True)
        return

    await cb.answer("⏳ Публикую в канал...")

    # Определяем, видео это или картинка
    is_video = False
    if (".mp4" in gen.result.lower() or "video" in gen.model_name.lower()):
        is_video = True

    try:
        # Отправляем медиа первым сообщением
        if is_video:
            await cb.bot.send_video(chat_id=CHANNEL_ID, video=gen.result)
        else:
            await cb.bot.send_photo(chat_id=CHANNEL_ID, photo=gen.result)

        # Отправляем промпт моноширинным текстом вторым сообщением
        prompt_text = (
            f"🎨 Модель: #{gen.model_name.replace('/', '_').replace('-', '_')}\n"
            f"📝 Промпт для копирования:\n\n"
            f"<pre>{gen.prompt}</pre>"
        )
        await cb.bot.send_message(
            chat_id=CHANNEL_ID,
            text=prompt_text,
            parse_mode="HTML",
            reply_markup=try_prompt_kb(gen_id)
        )

        await cb.message.answer("✅ <b>Успешно опубликовано в канале!</b>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sharing to channel: {e}")
        await cb.message.answer(
            f"❌ Ошибка публикации. Проверьте, добавлен ли бот в канал как администратор.\n"
            f"Или ссылка на файл уже устарела.\n{e}"
        )

@router.callback_query(F.data.startswith("run_gen:"))
async def run_shared_gen_cb(cb: CallbackQuery, state: FSMContext, session: AsyncSession):
    gen_id = int(cb.data.split(":")[1])
    res = await session.execute(select(Generation).where(Generation.id == gen_id))
    gen = res.scalar_one_or_none()

    if not gen:
        await cb.answer("❌ Генерация не найдена", show_alert=True)
        return

    # Устанавливаем пользователю эту модель
    user_res = await session.execute(select(User).where(User.telegram_id == cb.from_user.id))
    user = user_res.scalar_one()
    user.current_model = gen.model_name
    await session.commit()

    await cb.message.delete()

    ALL_MODELS = {}
    for category, families in MODEL_CATALOG.items():
        for fam_key, fam_data in families.items():
            for model in fam_data["models"]:
                ALL_MODELS[model["id"]] = {**model, "category": category}

    model_info = ALL_MODELS.get(gen.model_name)
    if not model_info:
        await cb.message.answer("❌ Модель больше не поддерживается.")
        return

    category = model_info.get("category", "gen_text")

    # Если модель требует референс (video, img2vid), просим фото
    is_img_model = "image-to" in gen.model_name or "img2vid" in model_info["name"].lower() or "first-last" in gen.model_name or "motion" in gen.model_name
    if is_img_model or category == "gen_video":
        await state.set_state(GenState.waiting_for_input)
        await state.update_data(prompt=gen.prompt) 
        await cb.message.answer(
            f"✅ Модель <b>{model_info['name']}</b> выбрана!\n\n"
            f"Эта модель требует изображение. Пожалуйста, отправьте <b>фотографию</b> (референс), "
            f"а промпт мы подставим автоматически:\n\n<code>{gen.prompt}</code>",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb()
        )
        return

    # Запускаем сразу, если модель может работать только по тексту
    await cb.answer("🚀 Запускаю...")
    if category in ["gen_image", "gen_nano_banana"]:
        await state.set_state(GenState.generating)
        await run_image_generation(cb.message, session, gen.prompt, reference_images=[], state=state)
    else:
        cb.message.text = gen.prompt
        await state.set_state(GenState.generating)
        await run_simple_generation(cb.message, user, session, model_info, category)

@router.callback_query(F.data.startswith("edit_gen:"))
async def edit_shared_gen_cb(cb: CallbackQuery, state: FSMContext, session: AsyncSession):
    gen_id = int(cb.data.split(":")[1])
    res = await session.execute(select(Generation).where(Generation.id == gen_id))
    gen = res.scalar_one_or_none()

    if not gen:
        await cb.answer("❌ Генерация не найдена", show_alert=True)
        return

    user_res = await session.execute(select(User).where(User.telegram_id == cb.from_user.id))
    user = user_res.scalar_one()
    user.current_model = gen.model_name
    await session.commit()

    await state.set_state(GenState.waiting_for_input)

    await cb.message.delete()
    await cb.message.answer(
        f"✅ Модель <b>{gen.model_name}</b> выбрана.\n\n"
        f"Вы можете скопировать оригинальный промпт, изменить его и отправить мне:\n\n"
        f"<code>{gen.prompt}</code>\n\n"
        f"Или просто отправьте свои фото/видео референсы.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb()
    )
    await cb.answer()
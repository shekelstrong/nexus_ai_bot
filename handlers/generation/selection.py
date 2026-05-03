import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import (
    main_menu, model_families_menu, models_list_menu, back_to_menu_kb,
    nano_banana_menu, video_category_menu, text_models_menu, prompt_menu,
    video_prompt_duration_menu, video_format_menu, video_duration_menu,
    post_video_gen_kb, image_size_menu
)
from database.models import User
from model_config import MODEL_CATALOG
from states.generation_states import GenState
from utils.logger import logger

router = Router(name="selection_router")

# Извлекаем описания моделей из нового конфига
MODEL_INFO = {}
for category, families in MODEL_CATALOG.items():
    for family_key, family_data in families.items():
        for model in family_data["models"]:
            MODEL_INFO[model["id"]] = {
                "name": model["name"],
                "category": category,
                "family": family_key,
                "description": model.get("description", "")
            }

SIZE_PROMPTS = {
    "1:1": " --ar 1:1",
    "16:9": " --ar 16:9",
    "9:16": " --ar 9:16",
    "4:3": " --ar 4:3",
    "3:4": " --ar 3:4",
    "21:9": " --ar 21:9",
    "2:3": " --ar 2:3",
    "3:2": " --ar 3:2"
}

# Маппинг размеров для GPT Image API (реальные пиксели)
GPT_IMAGE_SIZES = {
    "1:1": "1024x1024",
    "2:3": "1024x1536",
    "3:2": "1536x1024",
}

# Модели, поддерживающие выбор размера через API (не через промпт)
SIZE_API_MODELS = {"openai/gpt-5.4-image-2", "openai/gpt-5-image", "openai/gpt-5-image-mini"}

STYLE_PROMPTS = {
    "Anime 🌸": ", anime style, vibrant, detailed illustration, by Makoto Shinkai, studio ghibli",
    "Photo 📷": ", photorealistic, 8k, professional photography, sharp focus, octane render, canon 5d",
    "Cyberpunk 🌃": ", cyberpunk style, neon lights, futuristic city, high detail, blade runner vibes",
    "Fantasy ✨": ", fantasy style, epic, cinematic lighting, matte painting, by Greg Rutkowski, dnd",
    "GTA V 🔫": ", GTA V loading screen style, grand theft auto art, vector illustration, cel shaded, highly detailed",
    "Minecraft 🧱": ", minecraft style, voxel art, 3d blocky render, rtx on, vibrant colors",
    "Pixar 🧸": ", disney pixar style, 3d render, cute, expressive, high quality, render man",
    "Lego 🧱": ", lego style, plastic texture, depth of field, tilt shift, macro photography",
    "Barbie 🎀": ", barbie world style, pink aesthetic, plastic doll texture, dreamhouse vibes",
    "Dark Souls ⚔️": ", dark souls style, dark fantasy, gloomy, eldritch, fromsoftware artstyle",
    "Soviet Poster ☭": ", soviet propaganda poster style, constructivism, bold red and black colors, geometric shapes, vintage texture",
    "Oil Painting 🎨": ", oil painting, thick brushstrokes, van gogh style, starry night, textured",
    "Pencil Sketch ✏️": ", charcoal sketch, graphite pencil, rough paper texture, black and white, hand drawn",
    "Watercolor 💧": ", watercolor painting, soft colors, wet on wet, paper texture, dreamy",
    "Ukiyo-e 🌊": ", ukiyo-e style, japanese woodblock print, hokusai, traditional art, flat colors",
    "Vaporwave 📼": ", vaporwave aesthetic, 80s retro, neon purple and blue, glitch art, vhs effect",
    "Low Poly 🔷": ", low poly 3d art, minimal, geometric, pastel colors, blender cycle render",
    "Isometric 🎲": ", isometric view, 3d render, cute, diorama, detailed, orthographic",
    "Claymation 🧱": ", plasticine, claymation style, stop motion, aardman animation, fingerprint texture",
    "Unreal Engine 🎮": ", unreal engine 5 render, lumen, nanite, 8k, hyperrealistic, cinematic",
    "Sticker 🏷️": ", die-cut sticker, white border, vector art, cute, simple",
    "Tattoo 🐉": ", tattoo design, blackwork, linework, ink on skin, high contrast",
    "Graffiti 🎨": ", street art, graffiti, spray paint, urban wall texture, vibrant",
    "Logo 📐": ", vector logo, simple, minimalist, flat design, 2d, on white background"
}
STYLES_LIST = list(STYLE_PROMPTS.keys())

CATEGORY_IMAGES = {
    "gen_nano_banana": "assets/nano_banana.jpg"
}

FAMILY_IMAGES = {
    "seedream": "assets/seedream.jpg",
    "gemini_image": "assets/gpt_images.jpg"
}

async def _send_menu(callback: CallbackQuery, text: str, kb: InlineKeyboardMarkup, img_path: str = None):
    """Умный хелпер для переключения между текстовыми меню и меню с картинками"""
    if img_path and os.path.exists(img_path):
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer_photo(
            FSInputFile(img_path),
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        if callback.message.photo or callback.message.video or callback.message.document:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except:
                pass
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            try:
                await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                try:
                    await callback.message.delete()
                except:
                    pass
                await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("cat:"))
async def select_category_callback(callback: CallbackQuery, state: FSMContext):
    try:
        category = callback.data.split(":")[1]
        img_path = CATEGORY_IMAGES.get(category)

        if category == "gen_nano_banana":
            await _send_menu(callback, "<b>Nano Banana</b>\nВыберите модель:", nano_banana_menu(), img_path)

        elif category == "gen_text":
            await _send_menu(callback, "<b>Текстовые модели</b>\nВыберите бренд:", text_models_menu(), img_path)

        elif category == "gen_video":
            await _send_menu(callback, "<b>Генерация видео</b>\nВыберите тип:", video_category_menu(), img_path)

        elif category == "gen_prompt":
            await _send_menu(callback, "<b>✨ Промпт</b>\nПолучите промпт по референсному изображению:", prompt_menu(), img_path)

        elif category == "gen_image":
            await _send_menu(callback, "<b>Генерация изображений</b>\nВыберите семейство моделей:", model_families_menu(category), img_path)

        elif category == "gen_search":
            await _send_menu(callback, "<b>Поисковые модели</b>\nВыберите семейство моделей:", model_families_menu(category), img_path)

        else:
            await _send_menu(callback, "Выберите категорию", model_families_menu(category), img_path)

    except Exception as e:
        logger.error(f"Error in category selection: {e}")
        await callback.message.answer("Меню устарело. Вызовите /start")
    await callback.answer()

@router.callback_query(F.data.startswith("family:"))
async def select_family_callback(callback: CallbackQuery):
    category, family = callback.data.split(":")[1:]
    img_path = FAMILY_IMAGES.get(family)
    
    await _send_menu(
        callback,
        "<b>Выберите конкретную модель:</b>",
        models_list_menu(category, family),
        img_path
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery, state: FSMContext):
    # Не очищаем state полностью — сохраняем промпт и данные модели,
    # чтобы пользователь мог вернуться и продолжить
    current_data = await state.get_data()
    saved_prompt = current_data.get("saved_prompt", "")
    saved_model = current_data.get("saved_model", current_data.get("current_model", ""))
    
    await state.clear()
    # Восстанавливаем сохранённые данные
    if saved_prompt:
        await state.update_data(saved_prompt=saved_prompt)
    if saved_model:
        await state.update_data(saved_model=saved_model)
    
    await _send_menu(
        callback,
        "<b>Главное меню:</b>\nВыберите действие:",
        main_menu(),
        img_path=None
    )
    await callback.answer()


@router.callback_query(F.data == "use_generated_prompt")
async def use_generated_prompt_handler(callback: CallbackQuery, state: FSMContext):
    """Пользователь нажал «Использовать промпт» — сохраняем и предлагаем выбрать модель."""
    data = await state.get_data()
    saved_prompt = data.get("saved_prompt", "")
    
    if not saved_prompt:
        await callback.answer("Промпт не найден, начните заново", show_alert=True)
        return
    
    # Промпт сохранён, предлагаем выбрать категорию/модель
    await _send_menu(
        callback,
        "<b>Промпт сохранён! ✅</b>\n\n"
        f"Ваш промпт: <code>{saved_prompt[:200]}{'...' if len(saved_prompt) > 200 else ''}</code>\n\n"
        "Теперь выберите модель для генерации:",
        main_menu(),
        img_path=None
    )
    await callback.answer()

@router.callback_query(F.data == "restart_gen")
async def restart_gen_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GenState.waiting_for_input)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    data = await state.get_data()
    style_name = data.get("style", "Без стиля")
    
    await callback.message.answer(
        f"🔄 <b>Новая генерация (те же настройки)</b>\n"
        f"Текущий стиль: <b>{style_name}</b>\n\n"
        f"✍️ Напишите новый промпт (и/или прикрепите до 3 фото в качестве референсов).",
        reply_markup=back_to_menu_kb(), 
        parse_mode="HTML"
    )
    await callback.answer()

async def show_styles_page(callback: CallbackQuery, state: FSMContext, page: int, skipped_size: bool = False, is_new_msg: bool = False):
    items_per_page = 4
    total_pages = (len(STYLES_LIST) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_styles = STYLES_LIST[start_idx:end_idx]

    kb_rows = []
    for i in range(0, len(page_styles), 2):
        row = [InlineKeyboardButton(text=page_styles[i], callback_data=f"style_{page_styles[i]}", style="primary")]
        if i+1 < len(page_styles):
            row.append(InlineKeyboardButton(text=page_styles[i+1], callback_data=f"style_{page_styles[i+1]}", style="primary"))
        kb_rows.append(row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"stylepage_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"stylepage_{page+1}"))
    
    if nav_row:
        kb_rows.append(nav_row)

    kb_rows.append([InlineKeyboardButton(text="🚫 Без стиля", callback_data="style_none")])
    kb_rows.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")])

    data = await state.get_data()
    ratio = data.get("ratio", "1:1")
    name = data.get("current_model_name", "Модель")
    desc = data.get("current_model_desc", "")
    
    desc_text = f"\nℹ️ <i>{desc}</i>\n" if desc else ""

    if skipped_size:
        text = f"✅ Выбрана: <b>{name}</b>{desc_text}\nТеперь выберите <b>художественный стиль</b>:"
    else:
        text = f"✅ Размер <b>{ratio}</b> установлен!{desc_text}\nТеперь выберите <b>художественный стиль</b>:"

    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    if is_new_msg:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            try: 
                await callback.message.delete()
            except: 
                pass
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

# --- Обработчики Промпта ---

@router.callback_query(F.data == "prompt_for_image")
async def prompt_for_image_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Generate a descriptive image prompt from a reference photo."""
    await state.clear()
    await state.update_data(prompt_mode="image")
    await state.set_state(GenState.waiting_for_prompt_image)
    await callback.message.answer(
        "🖼️ <b>Промпт для фото</b>\n\n"
        "Отправьте <b>референсное изображение</b>, и я составлю подробный промпт для генерации аналогичного изображения.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "prompt_for_video")
async def prompt_for_video_handler(callback: CallbackQuery, state: FSMContext):
    """Video prompt generation — first choose duration."""
    await callback.message.edit_text(
        "🎥 <b>Промпт для видео</b>\n\nВыберите <b>длительность</b> видео:",
        parse_mode="HTML",
        reply_markup=video_prompt_duration_menu()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vprompt_dur:"))
async def vprompt_duration_handler(callback: CallbackQuery, state: FSMContext):
    duration = callback.data.split(":")[1]
    await state.clear()
    await state.update_data(prompt_mode="video", video_prompt_duration=duration)
    await state.set_state(GenState.waiting_for_prompt_image)
    await callback.message.answer(
        f"🖼️ <b>Промпт для видео ({duration} сек.)</b>\n\n"
        "Отправьте <b>референсное изображение</b>, и я составлю промпт для видео-генерации.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb()
    )
    await callback.answer()


# --- Обработчики формата/длительности видео ---

@router.callback_query(F.data.startswith("vformat:"))
async def video_format_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":", 1)
    ratio = parts[1] if len(parts) > 1 else "16:9"
    await state.update_data(video_ratio=ratio)
    await callback.message.edit_text(
        f"✅ Формат <b>{ratio}</b> выбран!\n\nТеперь выберите <b>длительность</b>:",
        parse_mode="HTML",
        reply_markup=video_duration_menu()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vduration:"))
async def video_duration_handler(callback: CallbackQuery, state: FSMContext):
    duration = callback.data.split(":")[1]
    await state.update_data(video_duration=duration)
    await state.set_state(GenState.waiting_for_input)
    data = await state.get_data()
    ratio = data.get("video_ratio", "16:9")
    current_model_name = data.get("current_model_name", "Модель")
    await callback.message.edit_text(
        f"✅ Настройки: <b>{ratio}</b>, <b>{duration} сек.</b>\n"
        f"Модель: <b>{current_model_name}</b>\n\n"
        "Отправьте фото или напишите описание:",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb()
    )
    await callback.answer()


# --- Кнопка «Снова в этой модели» ---

@router.callback_query(F.data.startswith("regen_model:"))
async def regen_model_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Restart generation in the same model without going back to menu."""
    model_id = callback.data.split(":", 1)[1]
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    if user:
        user.current_model = model_id
        await session.commit()

    info = MODEL_INFO.get(model_id, {})
    name = info.get("name", "Модель")
    category = info.get("category", "gen_text")

    # Сохраняем saved_prompt перед очисткой state
    state_data = await state.get_data()
    preserved_prompt = state_data.get("saved_prompt", "")

    await state.clear()
    await state.update_data(current_model_name=name)
    
    # Восстанавливаем сохранённый промпт
    if preserved_prompt:
        await state.update_data(saved_prompt=preserved_prompt)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    if category == "gen_video":
        await callback.message.answer(
            f"🔄 <b>Снова: {name}</b>\n\nВыберите формат видео:",
            parse_mode="HTML",
            reply_markup=video_format_menu()
        )
    elif category in ["gen_image", "gen_nano_banana"]:
        if category == "gen_image" and model_id in SIZE_API_MODELS:
            await callback.message.answer(
                f"🔄 <b>Снова: {name}</b>\n\nВыберите формат изображения:",
                parse_mode="HTML",
                reply_markup=image_size_menu()
            )
        else:
            await state.set_state(GenState.waiting_for_input)
            prompt_hint = ""
            if preserved_prompt:
                prompt_hint = f"\n\n💡 <i>У вас есть сохранённый промпт — просто отправьте /use или скопируйте:</i>\n<code>{preserved_prompt[:300]}</code>"
            await callback.message.answer(
                f"🔄 <b>Снова: {name}</b>\n\nОтправьте промпт (и фото при необходимости):{prompt_hint}",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb()
            )
    else:
        await state.set_state(GenState.waiting_for_input)
        await callback.message.answer(
            f"🔄 <b>Снова: {name}</b>\n\nНапишите ваш запрос:",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("set_model:"))
async def set_model_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    model_id = callback.data.split(":", 1)[1]
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    
    if user:
        user.current_model = model_id
        await session.commit()
        
    info = MODEL_INFO.get(model_id, {})
    name = info.get("name", "Модель")
    category = info.get("category", "gen_text")
    family = info.get("family", "")
    description = info.get("description", "")
    
    await state.clear()
    
    # Сохраняем данные модели, чтобы показать их на следующем шаге (выборе стиля)
    await state.update_data(current_model_name=name, current_model_desc=description)
    
    try:
        if callback.message.photo or callback.message.video or callback.message.document:
            await callback.message.edit_reply_markup(reply_markup=None)
        else:
            await callback.message.delete()
    except:
        pass
        
    desc_text = f"\nℹ️ <i>{description}</i>\n" if description else ""
    
    if category in ["gen_image", "gen_nano_banana"]:
        # Модели, поддерживающие выбор размера через API
        if category == "gen_image" and model_id in SIZE_API_MODELS:
            # Показываем меню выбора размера
            await callback.message.answer(
                f"✅ Выбрана: <b>{name}</b>{desc_text}\n\nВыберите <b>формат изображения</b>:",
                parse_mode="HTML",
                reply_markup=image_size_menu()
            )
            await callback.answer()
            return
        # Остальные модели — сразу в режим ввода без выбора размеров/стилей
        await state.update_data(ratio="1:1", size_prompt="", style_prompt="", style="Без стиля", image_size=None)
        text = f"✅ Выбрана: <b>{name}</b>{desc_text}\n\nОтправьте промпт (и фото-референс при необходимости):"
        await state.set_state(GenState.waiting_for_input)
        await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
        await callback.answer()
        return

    text = f"✅ Выбрана: <b>{name}</b>{desc_text}\n"
    
    if category == "gen_text":
        text += "Теперь просто напишите ваш <b>запрос (промпт)</b>."
        await state.set_state(GenState.waiting_for_input)
        await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    elif category == "gen_search":
        text += "🔍 Теперь напишите ваш <b>вопрос для поиска</b>."
        await state.set_state(GenState.waiting_for_input)
        await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    elif category == "gen_video":
        if "motion-control" in model_id:
            text += "<b>Шаг 1:</b> Отправьте <b>фотографию персонажа</b>, которого хотите анимировать."
            await state.set_state(GenState.waiting_for_first_image)
            await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
        elif "first-last" in model_id:
            text += "<b>Шаг 1:</b> Отправьте <b>первую картинку</b> (начальный кадр)."
            await state.set_state(GenState.waiting_for_first_image)
            await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
        else:
            # Для всех остальных видео-моделей: выбор формата
            await callback.message.answer(
                f"✅ Выбрана: <b>{name}</b>{desc_text}\n\nВыберите <b>формат</b> видео:",
                parse_mode="HTML",
                reply_markup=video_format_menu()
            )
    else:
        text += "Теперь просто напишите ваш <b>запрос (промпт)</b>."
        await state.set_state(GenState.waiting_for_input)
        await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("size_"))
async def set_size(cb: CallbackQuery, state: FSMContext):
    ratio = cb.data.split("_")[1]
    size_prompt = SIZE_PROMPTS.get(ratio, "")
    await state.update_data(ratio=ratio, size_prompt=size_prompt)
    await show_styles_page(cb, state, page=0)
    await cb.answer()

@router.callback_query(F.data.startswith("isize:"))
async def set_image_size_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор размера для GPT Image моделей."""
    ratio = callback.data.split(":", 1)[1]
    api_size = GPT_IMAGE_SIZES.get(ratio, "1024x1024")
    await state.update_data(
        ratio=ratio,
        size_prompt="",
        style_prompt="",
        style="Без стиля",
        image_size=api_size
    )
    data = await state.get_data()
    name = data.get("current_model_name", "Модель")
    
    try:
        await callback.message.edit_text(
            f"✅ Размер <b>{ratio}</b> ({api_size}) установлен!\n"
            f"Модель: <b>{name}</b>\n\n"
            "✍️ Отправьте промпт (и фото-референс при необходимости):",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb()
        )
    except Exception:
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            f"✅ Размер <b>{ratio}</b> ({api_size}) установлен!\n"
            f"Модель: <b>{name}</b>\n\n"
            "✍️ Отправьте промпт (и фото-референс при необходимости):",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb()
        )
    
    await state.set_state(GenState.waiting_for_input)
    await callback.answer()

@router.callback_query(F.data.startswith("stylepage_"))
async def style_page_handler(cb: CallbackQuery, state: FSMContext):
    page = int(cb.data.split("_")[1])
    await show_styles_page(cb, state, page)
    await cb.answer()

@router.callback_query(F.data.startswith("style_"))
async def set_style(cb: CallbackQuery, state: FSMContext):
    style = cb.data.replace("style_", "")
    if style == "none":
        style_prompt = ""
        style_name = "Без стиля"
    else:
        style_prompt = STYLE_PROMPTS.get(style, "")
        style_name = style
        
    await state.update_data(style=style_name, style_prompt=style_prompt)
    await state.set_state(GenState.waiting_for_input)
    
    text = (
        f"✅ <b>Стиль: {style_name}</b>\n\n"
        "✍️ Все готово! Теперь просто <b>напишите промпт</b> (описание картинки) и/или прикрепите <b>до 3 фото</b> в качестве референсов."
    )
    
    try:
        await cb.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    except Exception:
        try:
            await cb.message.delete()
        except:
            pass
        await cb.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    
    await cb.answer()
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import main_menu, model_families_menu, models_list_menu, back_to_menu_kb, nano_banana_menu
from database.models import User
from model_config import MODEL_CATALOG
from states.generation_states import GenState
from utils.logger import logger

router = Router(name="selection_router")

MODEL_INFO = {}
for category, families in MODEL_CATALOG.items():
    for family_key, family_data in families.items():
        for model in family_data["models"]:
            MODEL_INFO[model["id"]] = {
                "name": model["name"],
                "category": category,
                "family": family_key
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

@router.callback_query(F.data.startswith("cat:"))
async def select_category_callback(callback: CallbackQuery):
    try:
        category = callback.data.split(":")[1]
        titles = {
            "gen_text": "<b>Текстовые модели</b>",
            "gen_nano_banana": "<b>Nano Banana</b>",
            "gen_image": "<b>Генерация изображений</b>",
            "gen_video": "<b>Генерация видео</b>",
            "gen_search": "<b>Поисковые модели</b>"
        }
        title = titles.get(category, "Выберите категорию")
        
        if category == "gen_nano_banana":
            await callback.message.edit_text(
                f"{title}\nВыберите модель:",
                reply_markup=nano_banana_menu(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"{title}\nВыберите семейство моделей:",
                reply_markup=model_families_menu(category),
                parse_mode="HTML"
            )
    except Exception as e:
        await callback.message.answer("Меню устарело. Вызовите /start")
    await callback.answer()

@router.callback_query(F.data.startswith("family:"))
async def select_family_callback(callback: CallbackQuery):
    category, family = callback.data.split(":")[1:]
    await callback.message.edit_text(
        "<b>Выберите конкретную модель:</b>",
        reply_markup=models_list_menu(category, family),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.message.text:
        try:
            await callback.message.edit_text(
                "<b>Главное меню:</b>\nВыберите действие:",
                reply_markup=main_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await _send_menu_as_new_message(callback)
    else:
        await _send_menu_as_new_message(callback)
    await callback.answer()

async def _send_menu_as_new_message(callback: CallbackQuery):
    try:
        await callback.message.answer(
            "<b>Главное меню:</b>\nВыберите действие:",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send menu: {e}")

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
    
    await state.clear()
    
    # === НОВАЯ ЛОГИКА: ПРЕДЛАГАЕМ РАЗМЕРЫ ДЛЯ ИЗОБРАЖЕНИЙ ===
    if category in ["gen_image", "gen_nano_banana"]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1:1", callback_data="size_1:1"), InlineKeyboardButton(text="16:9", callback_data="size_16:9")],
            [InlineKeyboardButton(text="9:16", callback_data="size_9:16"), InlineKeyboardButton(text="4:3", callback_data="size_4:3")],
            [InlineKeyboardButton(text="3:4", callback_data="size_3:4"), InlineKeyboardButton(text="21:9", callback_data="size_21:9")],
            [InlineKeyboardButton(text="2:3", callback_data="size_2:3"), InlineKeyboardButton(text="3:2", callback_data="size_3:2")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
        text = f"✅ <b>Модель установлена!</b>\nВыбрана: <b>{name}</b>\n\nТеперь выберите соотношение сторон (размер):"
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    # === ЛОГИКА ДЛЯ ОСТАЛЬНЫХ МОДЕЛЕЙ (БЕЗ РАЗМЕРОВ) ===
    text = f"✅ <b>Модель установлена!</b>\nВыбрана: <b>{name}</b>\n\n"
    
    if category == "gen_text":
        text += "Теперь просто напишите ваш <b>запрос (промпт)</b>."
        await state.set_state(GenState.waiting_for_input)
    elif category == "gen_search":
        text += "🔍 Теперь напишите ваш <b>вопрос для поиска</b>."
        await state.set_state(GenState.waiting_for_input)
    elif category == "gen_video":
        if "motion-control" in model_id:
            text += "<b>Шаг 1:</b> Отправьте <b>фотографию персонажа</b>, которого хотите анимировать."
            await state.set_state(GenState.waiting_for_first_image)
        elif "first-last" in model_id or "first last" in model_id:
            text += "<b>Шаг 1:</b> Отправьте <b>первую картинку</b> (начальный кадр)."
            await state.set_state(GenState.waiting_for_first_image)
        elif "image-to-video" in model_id or "img2vid" in model_id or "reference-to-video" in model_id:
            text += "Теперь отправьте <b>фотографию</b>, которую нужно оживить."
            await state.set_state(GenState.waiting_for_input)
        elif "extend" in model_id:
            text += "Теперь отправьте <b>видео</b> для продолжения."
            await state.set_state(GenState.waiting_for_input)
        else:
            text += "Теперь напишите <b>описание видео</b> (промпт)."
            await state.set_state(GenState.waiting_for_input)
    else:
        text += "Теперь просто напишите ваш <b>запрос (промпт)</b>."
        await state.set_state(GenState.waiting_for_input)
        
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("size_"))
async def set_size(cb: CallbackQuery, state: FSMContext):
    ratio = cb.data.split("_")[1]
    size_prompt = SIZE_PROMPTS.get(ratio, "")
    await state.update_data(ratio=ratio, size_prompt=size_prompt)
    
    items = STYLES_LIST
    kb_rows = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(text=items[i], callback_data=f"style_{items[i]}")]
        if i+1 < len(items): 
            row.append(InlineKeyboardButton(text=items[i+1], callback_data=f"style_{items[i+1]}"))
        kb_rows.append(row)
    kb_rows.append([InlineKeyboardButton(text="🚫 Без стиля", callback_data="style_none")])
    kb_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    
    await cb.message.edit_text(
        f"✅ <b>Размер {ratio} установлен!</b>\n\nТеперь выберите <b>художественный стиль</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML"
    )
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
        
    # Сохраняем стиль в FSM Context
    await state.update_data(style=style_name, style_prompt=style_prompt)
    
    # Теперь ставим состояние для принятия промпта
    await state.set_state(GenState.waiting_for_input)
    
    text = (
        f"✅ <b>Стиль: {style_name}</b>\n\n"
        "✍️ Все готово! Теперь просто <b>напишите промпт</b> (описание картинки) и/или прикрепите <b>до 3 фото</b> как референсы в чат."
    )
    await cb.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await cb.answer()
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import main_menu, model_families_menu, models_list_menu, back_to_menu_kb # <-- ИМПОРТ
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

@router.callback_query(F.data.startswith("cat:"))
async def select_category_callback(callback: CallbackQuery):
    try:
        category = callback.data.split(":")[1]
        titles = {
            "gen_text": "📝 <b>Текстовые модели</b>",
            "gen_image": "🎨 <b>Генерация изображений</b>",
            "gen_video": "🎬 <b>Генерация видео</b>",
            "gen_search": "🔍 <b>Поисковые модели</b>"
        }
        title = titles.get(category, "🤖 Выберите категорию")
        
        await callback.message.edit_text(
            f"{title}\nВыберите семейство моделей:",
            reply_markup=model_families_menu(category),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer("⚠️ Меню устарело. Вызовите /start")
    await callback.answer()

@router.callback_query(F.data.startswith("family:"))
async def select_family_callback(callback: CallbackQuery):
    _, category, family = callback.data.split(":")
    await callback.message.edit_text(
        f"📂 <b>Выберите конкретную модель:</b>",
        reply_markup=models_list_menu(category, family),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Check if message has text content before attempting edit
    if callback.message.text:
        try:
            await callback.message.edit_text(
                "👋 <b>Главное меню:</b>\nВыберите действие:",
                reply_markup=main_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await _send_menu_as_new_message(callback)
    else:
        # For media messages or messages without text, send new message
        await _send_menu_as_new_message(callback)
    
    await callback.answer()

async def _send_menu_as_new_message(callback: CallbackQuery):
    """Helper function to send menu as a new message."""
    try:
        await callback.message.answer(
            "👋 <b>Главное меню:</b>\nВыберите действие:",
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

    text = f"✅ <b>Модель установлена!</b>\nВыбрана: <b>{name}</b>\n\n"

    await state.clear()

    # Логика инструкций в зависимости от категории модели
    if category == "gen_text":
        # Текстовые модели — ждут текст
        text += "✍️ Теперь просто напишите ваш <b>запрос (промпт)</b>."
        await state.set_state(GenState.waiting_for_input)
    elif category == "gen_search":
        # Поисковые модели — ждут текст
        text += "🔍 Теперь напишите ваш <b>вопрос для поиска</b>."
        await state.set_state(GenState.waiting_for_input)
    elif category == "gen_image":
        # Модели изображений — могут требовать изображение или текст
        # Проверяем по названию модели
        if "image" in model_id.lower() or "img" in name.lower():
            text += "🎨 Теперь отправьте <b>изображение</b> для обработки."
            await state.set_state(GenState.waiting_for_input)
        else:
            text += "🎨 Теперь напишите <b>описание изображения</b> (промпт)."
            await state.set_state(GenState.waiting_for_input)
    elif category == "gen_video":
        # Видео модели — проверяем тип
        if "motion-control" in model_id:
            text += "1️⃣ <b>Шаг 1:</b> Отправьте <b>фотографию персонажа</b>, которого хотите анимировать."
            await state.set_state(GenState.waiting_for_first_image)
        elif "first-last" in model_id or "first_last" in model_id:
            text += "1️⃣ <b>Шаг 1:</b> Отправьте <b>первую картинку</b> (начальный кадр)."
            await state.set_state(GenState.waiting_for_first_image)
        elif "image-to-video" in model_id or "img2vid" in model_id or "reference-to-video" in model_id:
            text += "📸 Теперь отправьте <b>фотографию</b>, которую нужно оживить."
            await state.set_state(GenState.waiting_for_input)
        elif "extend" in model_id:
            text += "📹 Теперь отправьте <b>видео</b> для продолжения."
            await state.set_state(GenState.waiting_for_input)
        else:
            # Text-to-video
            text += "🎬 Теперь напишите <b>описание видео</b> (промпт)."
            await state.set_state(GenState.waiting_for_input)
    else:
        # По умолчанию — текстовый запрос
        text += "✍️ Теперь просто напишите ваш <b>запрос (промпт)</b>."
        await state.set_state(GenState.waiting_for_input)

    await callback.message.delete()
    # ИСПОЛЬЗУЕМ МАЛЕНЬКУЮ КЛАВИАТУРУ
    await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()
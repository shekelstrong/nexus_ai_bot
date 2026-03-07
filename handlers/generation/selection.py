from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import main_menu, model_families_menu, models_list_menu, back_to_menu_kb, image_gen_mode_kb, references_ready_kb
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
        # Все модели изображений — предлагаем выбор режима
        text += "🎨 Выберите режим генерации:"
        await state.clear()
        await state.set_state(GenState.waiting_for_input) # Сбрасываем состояние
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=image_gen_mode_kb(), parse_mode="HTML")
        await callback.answer()
        return
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

# --- ОБРАБОТКА ВЫБОРА РЕЖИМА ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ---
@router.callback_query(F.data == "img_mode:references")
async def img_mode_references_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Пользователь выбрал генерацию с референсами"""
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    
    if user:
        model_id = user.current_model
        info = MODEL_INFO.get(model_id, {})
        name = info.get("name", "Модель")
        
        await state.update_data(reference_images=[]) # Очищаем список референсов
        await state.set_state(GenState.waiting_for_reference_images)
        
        await callback.message.edit_text(
            f"📸 <b>Режим с референсами</b>\n\n"
            f"Модель: <b>{name}</b>\n\n"
            f"Отправьте <b>до 3 изображений</b> для использования как референсы.\n"
            f"Когда закончите — нажмите кнопку ✅ Готово.",
            reply_markup=references_ready_kb(),
            parse_mode="HTML"
        )
    
    await callback.answer()

@router.callback_query(F.data == "img_mode:prompt")
async def img_mode_prompt_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Пользователь выбрал генерацию только по промпту"""
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    
    if user:
        model_id = user.current_model
        info = MODEL_INFO.get(model_id, {})
        name = info.get("name", "Модель")
        
        await state.set_state(GenState.waiting_for_image_prompt)
        
        await callback.message.edit_text(
            f"✍️ <b>Режим только с промптом</b>\n\n"
            f"Модель: <b>{name}</b>\n\n"
            f"Напишите <b>описание изображения</b> (промпт).",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML"
        )
    
    await callback.answer()

@router.callback_query(F.data == "references_done")
async def references_done_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Пользователь закончил загрузку референсов"""
    data = await state.get_data()
    reference_images = data.get("reference_images", [])
    
    if not reference_images:
        await callback.answer("❌ Сначала отправьте хотя бы 1 референс!", show_alert=True)
        return
    
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    
    if user:
        model_id = user.current_model
        info = MODEL_INFO.get(model_id, {})
        name = info.get("name", "Модель")
        
        await state.set_state(GenState.waiting_for_image_prompt)
        
        refs_count = len(reference_images)
        await callback.message.edit_text(
            f"✅ <b>Референсы загружены!</b>\n\n"
            f"Модель: <b>{name}</b>\n"
            f"📸 Референсов: {refs_count} шт.\n\n"
            f"Теперь напишите <b>описание изображения</b> (промпт).",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML"
        )
    
    await callback.answer()
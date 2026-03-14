import uuid
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from keyboards.inline import main_menu, model_families_menu, nano_banana_menu
from config import TEXTS, ADMIN_IDS
from handlers.admin.notifications import notify_admin_new_user, notify_referrer_new_referral
from handlers.generation.selection import CATEGORY_IMAGES
from utils.logger import logger

router = Router(name="start_router")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    
    # Реферальная система: достаем referral code из ссылки
    args = message.text.split()
    referrer_code = None
    start_param = None

    if len(args) > 1:
        start_param = args[1]

        # Проверяем, не является ли это параметром оплаты
        if start_param.startswith("pay_success_"):
            order_id = start_param.replace("pay_success_", "")
            await handle_pay_success(message, session, order_id)
            return
        elif start_param == "pay_failed":
            await handle_pay_failed(message)
            return

        # Если не оплата, проверяем на реферальный код
        referrer_code = start_param

    # ЛОГИРОВАНИЕ ДЛЯ Отладки
    logger.info(f"🚀 /start от {message.from_user.id} (@{message.from_user.username}), реферер (code): {referrer_code}")

    # Проверка, есть ли уже такой пользователь в базе
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        # Находим рефовода по referral_code (HE по telegram_id!)
        referrer_internal_id = None
        referrer_user = None

        if referrer_code:
            ref_result = await session.execute(select(User).where(User.referral_code == referrer_code))
            referrer_user = ref_result.scalar_one_or_none()
            logger.info(f"🔍 Поиск рефовода по referral_code '{referrer_code}': {'найден' if referrer_user else 'HE НАЙДЕН'}")

            if referrer_user:
                referrer_internal_id = referrer_user.id  # Внутренний ID для FK
                logger.info(f"✅ Рефовод найден: internal_id={referrer_internal_id}, TG={referrer_user.telegram_id}, @{referrer_user.username}, code={referrer_user.referral_code}")
            else:
                logger.warning(f"⚠️ referral_code '{referrer_code}' не найден в базе")

        # Создаем нового пользователя с генерацией обязательного referral_code
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referrer_id=referrer_internal_id,  # Сохраняем внутренний ID (FK)
            referral_code=str(uuid.uuid4())[:8]  # Генерация уникального короткого кода
        )
        session.add(user)

        try:
            await session.commit()
            logger.info(f"✅ Пользователь {message.from_user.id} сохранен в БД, referrer_id={user.referrer_id}, referral_code={user.referral_code}")

            # Уведомляем реферера, если он есть
            if referrer_user:
                logger.info(f"📨 Отправка уведомления рефоводу {referrer_user.telegram_id}")
                await notify_referrer_new_referral(
                    bot=message.bot,
                    referrer_id=referrer_user.telegram_id,
                    new_user_id=message.from_user.id,
                    new_user_username=message.from_user.username,
                    welcome_bonus=0.0,  # приветственного бонуса нет, только от пополнений
                )
                # Уведомление админам о новом пользователе с рефоводом
                await notify_admin_new_user(
                    bot=message.bot,
                    user_id=message.from_user.id,
                    username=message.from_user.username,
                    referrer_id=referrer_user.telegram_id,
                    referrer_username=referrer_user.username,
                    referrer_bonus=0.0,
                )
            else:
                logger.info("📨 Рефовод не найден, отправка уведомления админу без реферала")
                # Нет реферера или реферер не найден - просто уведомляем админа
                await notify_admin_new_user(
                    bot=message.bot,
                    user_id=message.from_user.id,
                    username=message.from_user.username,
                    referrer_id=None,
                    referrer_username=None,
                    referrer_bonus=0.0,
                )

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка при сохранении пользователя: {e}")

    # Текст приветствия из твоего конфига
    text = TEXTS["ru"]["welcome"]
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


async def handle_pay_success(message: Message, session: AsyncSession, order_id: str):
    """Обработка успешной оплаты после возврата из Platega."""
    from services.payments import get_purchase_details
    logger.info(f"💳 Обработка успешной оплаты: order_id={order_id}")

    parts = order_id.split("_")
    if len(parts) < 3:
        await message.answer(
            "<b>Ошибка обработки платежа</b>\n\n"
            "Некорректный формат заказа. Обратитесь в поддержку.",
            parse_mode="HTML"
        )
        return

    item_type = parts[0]
    item_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else parts[0]

    details = get_purchase_details(item_type, item_id)
    text = "<b>Оплата прошла успешно!</b>\n\nНачислено:\n"

    if details.get('tokens', 0) > 0:
        if details.get('duration_days', 0) > 0:
            daily = details['tokens'] // details['duration_days']
            text += f"🪙 <b>{details['tokens']} токенов</b> ({daily} в день)\n"
        else:
            text += f"🪙 <b>{details['tokens']} токенов</b> (бессрочно)\n"

    if details.get('video', 0) > 0:
        text += f"🎬 <b>{details['video']} видео</b> (бессрочно)\n"

    if details.get('duration_days', 0) > 0:
        text += f"\n⏳ Срок: <b>{details['duration_days']} дней</b>"

    text += "\n\nСпасибо за покупку! 🎉"

    await message.answer(text, parse_mode="HTML")
    await message.answer(TEXTS["ru"]["welcome"], reply_markup=main_menu(), parse_mode="HTML")


async def handle_pay_failed(message: Message):
    """Обработка неудачной оплаты после возврата из Platega."""
    logger.warning(f"❌ Оплата не прошла для пользователя {message.from_user.id}")
    await message.answer(
        "❌ <b>Оплата не прошла</b>\n\n"
        "Попробуйте еще раз или выберите другой способ оплаты.\n\n"
        "Если проблема повторяется, обратитесь в поддержку.",
        parse_mode="HTML"
    )
    await message.answer(TEXTS["ru"]["welcome"], reply_markup=main_menu(), parse_mode="HTML")


def support_menu() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками поддержки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Поддержка", url="https://t.me/Anna16lu")],
        [InlineKeyboardButton(text="⚙️ Техническая поддержка", url="https://t.me/nedopekin")],
        [InlineKeyboardButton(text="📄 Политика конфиденциальности", url="https://telegra.ph/Politika-konfidencialnosti-08-15-17")],
        [InlineKeyboardButton(text="📜 Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-08-15-10")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])


@router.callback_query(F.data == "support")
async def support_cb(cb: CallbackQuery):
    """Обработчик кнопки Поддержка"""
    text = "<b>Поддержка Nexus AI</b>\n\nВыберите раздел:"
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=support_menu())
    await cb.answer()


# --- НОВЫЕ КОМАНДЫ ИЗ МЕНЮ ---

@router.message(Command("photo"))
async def cmd_photo(message: Message, state: FSMContext):
    """Обработчик команды /photo - Изображения"""
    await state.clear()
    category = "gen_image"
    img_path = CATEGORY_IMAGES.get(category)
    text = "<b>Генерация изображений</b>\nВыберите семейство моделей:"
    kb = model_families_menu(category)
    
    if img_path and os.path.exists(img_path):
        await message.answer_photo(FSInputFile(img_path), caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("nanobanana"))
async def cmd_nanobanana(message: Message, state: FSMContext):
    """Обработчик команды /nanobanana - Nano Banana"""
    await state.clear()
    category = "gen_nano_banana"
    img_path = CATEGORY_IMAGES.get(category)
    text = "<b>Nano Banana</b>\nВыберите модель:"
    kb = nano_banana_menu()
    
    if img_path and os.path.exists(img_path):
        await message.answer_photo(FSInputFile(img_path), caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("s"))
async def cmd_search(message: Message, state: FSMContext):
    """Обработчик команды /s - Интернет поиск"""
    await state.clear()
    category = "gen_search"
    text = "<b>Поисковые модели</b>\nВыберите семейство моделей:"
    kb = model_families_menu(category)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("privacy"))
async def cmd_privacy(message: Message, state: FSMContext):
    """Обработчик команды /privacy - Соглашения (Поддержка)"""
    await state.clear()
    text = "<b>Поддержка Nexus AI</b>\n\nВыберите раздел:"
    await message.answer(text, reply_markup=support_menu(), parse_mode="HTML")
import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from keyboards.inline import main_menu
from config import TEXTS, ADMIN_IDS
from handlers.admin.notifications import notify_admin_new_user, notify_referrer_new_referral
from utils.logger import logger

router = Router(name="start_router")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()

    # Реферальная система: достаем ID пригласившего из ссылки
    args = message.text.split()
    referrer_telegram_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_telegram_id = int(args[1])
        if referrer_telegram_id == message.from_user.id:
            referrer_telegram_id = None
    
    # ЛОГИРОВАНИЕ для отладки
    logger.info(f"🔍 /start от {message.from_user.id} (@{message.from_user.username}), реферер: {referrer_telegram_id}")

    # Проверка, есть ли уже такой пользователь в базе
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()

    is_new_user = False

    if not user:
        is_new_user = True
        
        # Находим внутреннего referrer_id по telegram_id
        referrer_internal_id = None
        referrer_user = None
        if referrer_telegram_id:
            ref_result = await session.execute(
                select(User).where(User.telegram_id == referrer_telegram_id)
            )
            referrer_user = ref_result.scalar_one_or_none()
            logger.info(f"🔍 Поиск рефовода по TG ID {referrer_telegram_id}: {'найден' if referrer_user else 'НЕ НАЙДЕН'}")
            if referrer_user:
                referrer_internal_id = referrer_user.id  # Внутренний ID для FK
                logger.info(f"✅ Рефовод найден: internal_id={referrer_internal_id}, TG={referrer_user.telegram_id}, @{referrer_user.username}")

        # Создаем нового пользователя с генерацией обязательного referral_code
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referrer_id=referrer_internal_id,  # Сохраняем внутренний ID (FK)
            referral_code=str(uuid.uuid4())[:8] # Генерация уникального короткого кода
        )
        session.add(user)
        try:
            await session.commit()
            logger.info(f"✅ Пользователь {message.from_user.id} сохранен в БД, referrer_id={user.referrer_id}")

            # Уведомляем реферера, если он есть
            if referrer_user:
                logger.info(f"📤 Отправка уведомления рефоводу {referrer_user.telegram_id}")
                # Уведомление рефоводу
                await notify_referrer_new_referral(
                    bot=message.bot,
                    referrer_id=referrer_user.telegram_id,
                    new_user_id=message.from_user.id,
                    new_user_username=message.from_user.username,
                    welcome_bonus=0.0,  # Приветственного бонуса нет, только % от пополнений
                )

                logger.info(f"📤 Отправка уведомления админам о реферале")
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
                logger.info(f"⚠️ Рефовод не найден, отправка уведомления админу без реферала")
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
            print(f"Ошибка при сохранении пользователя: {e}")

    # Текст приветствия из твоего конфига
    text = TEXTS["ru"]["welcome"]

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


def support_menu() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками поддержки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/Anna16lu")],
        [InlineKeyboardButton(text="🛠 Техническая поддержка", url="https://t.me/nedopekin")],
        [InlineKeyboardButton(text="📄 Политика конфиденциальности", url="https://telegra.ph/Politika-konfidencialnosti-08-15-17")],
        [InlineKeyboardButton(text="📋 Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-08-15-10")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ])


@router.callback_query(F.data == "support")
async def support_cb(cb: CallbackQuery):
    """Обработчик кнопки Поддержка"""
    text = "👨‍💻 <b>Поддержка Nexus AI</b>\n\nВыберите раздел:"
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=support_menu())
    await cb.answer()
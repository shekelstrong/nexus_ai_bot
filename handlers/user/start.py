import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from keyboards.inline import main_menu
from config import TEXTS

router = Router(name="start_router")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()

    # Реферальная система: достаем ID пригласившего из ссылки
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == message.from_user.id:
            referrer_id = None

    # Проверка, есть ли уже такой пользователь в базе
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()

    if not user:
        # Создаем нового пользователя с генерацией обязательного referral_code
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referrer_id=referrer_id,
            referral_code=str(uuid.uuid4())[:8] # Генерация уникального короткого кода
        )
        session.add(user)
        try:
            await session.commit()

            # Уведомляем реферера, если он есть
            if referrer_id:
                try:
                    await message.bot.send_message(referrer_id, "🎉 У вас новый реферал!")
                except:
                    pass
        except Exception as e:
            await session.rollback()
            # В случае ошибки базы данных мы увидим её в логах службы
            print(f"Ошибка при сохранении пользователя: {e}")

    # Текст приветствия из твоего конфига
    text = TEXTS["ru"]["welcome"]

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


@router.callback_query(F.data == "support")
async def support_cb(cb: CallbackQuery):
    """Обработчик кнопки Поддержка"""
    text = (
        "👨‍💻 <b>Поддержка Nexus AI</b>\n\n"
        "Если у вас возникли вопросы или проблемы, напишите нам:\n\n"
        "📧 Email: <code>support@nexus-ai.bot</code>\n"
        "📱 Telegram: <a href='https://t.me/nexus_ai_support'>@nexus_ai_support</a>\n\n"
        "⏰ Мы отвечаем в течение 24 часов."
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await cb.answer()
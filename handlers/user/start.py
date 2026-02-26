from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from keyboards.inline import main_menu # Импорт с подчеркиванием
from config import TEXTS

router = Router(name="start_router")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    
    # Реферальная система
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == message.from_user.id:
            referrer_id = None

    # Проверка/создание юзера
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referrer_id=referrer_id
        )
        session.add(user)
        await session.commit()
        
        # Начисление бонуса рефереру (если есть)
        if referrer_id:
            ref_res = await session.execute(select(User).where(User.telegram_id == referrer_id))
            referrer = ref_res.scalar_one_or_none()
            if referrer:
                try:
                    await message.bot.send_message(referrer_id, "🎉 У вас новый реферал!")
                except: pass

    # Текст приветствия (язык пока дефолтный ru)
    text = TEXTS["ru"]["welcome"]
    
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")

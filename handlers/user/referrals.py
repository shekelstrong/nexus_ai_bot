import qrcode
import io
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from keyboards.inline import back_to_menu_kb
from config import REF_LEVELS
from utils.logger import logger

router = Router(name="referrals_router")

async def _send_referral_msg(bot, chat_id, user_id, session: AsyncSession, old_message: Message = None):
    res = await session.execute(select(User).where(User.telegram_id == user_id))
    user = res.scalar_one_or_none()

    if not user:
        if old_message:
            await bot.send_message(chat_id, "Пользователь не найден")
        return

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user.referral_code}"

    # Генерация QR кода
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(ref_link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    qr_photo = BufferedInputFile(img_byte_arr.getvalue(), filename="qr.png")

    # Получаем статистику по приглашенным (прямые рефералы 1 уровня)
    res_refs = await session.execute(select(User).where(User.referrer_id == user.id))
    referrals = res_refs.scalars().all()
    refs_count = len(referrals)

    level1_pct = int(REF_LEVELS[0] * 100)
    level2_pct = int(REF_LEVELS[1] * 100)
    level3_pct = int(REF_LEVELS[2] * 100)

    text = (
        f"🎁 <b>Реферальная программа</b>\n\n"
        f"Приглашайте друзей и получайте процент от их покупок на 3 уровнях:\n"
        f"🥇 1 уровень: <b>{level1_pct}%</b>\n"
        f"🥈 2 уровень: <b>{level2_pct}%</b>\n"
        f"🥉 3 уровень: <b>{level3_pct}%</b>\n\n"
        f"👥 <b>Ваши приглашенные:</b> {refs_count} чел.\n"
        f"💰 <b>Заработано:</b> {user.referral_balance:.2f}₽\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{ref_link}</code>\n"
        f"🔑 <b>Ваш код:</b> <code>{user.referral_code}</code>"
    )

    if old_message:
        try:
            await old_message.delete()
        except:
            pass

    await bot.send_photo(
        chat_id=chat_id,
        photo=qr_photo,
        caption=text,
        parse_mode="HTML",
        reply_markup=back_to_menu_kb()
    )

@router.callback_query(F.data == "referrals")
async def show_referrals_cb(cb: CallbackQuery, session: AsyncSession):
    """Обработчик для inline-кнопки Рефералка"""
    await _send_referral_msg(cb.bot, cb.message.chat.id, cb.from_user.id, session, cb.message)
    await cb.answer()

@router.message(Command("earn"))
async def cmd_earn(message: Message, session: AsyncSession):
    """Обработчик команды /earn из меню"""
    await _send_referral_msg(message.bot, message.chat.id, message.from_user.id, session)
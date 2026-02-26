from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, ReferralStats, Transaction, TransactionType
from keyboards.inline import main_menu

router = Router(name="referrals_router")


async def count_referrals_by_level(session: AsyncSession, user_id: int, level: int) -> int:
    """Считает количество рефералов определенного уровня"""
    # В таблице ReferralStats мы храним связи: кто (referrer_id) кого (referral_id) и какой уровень (level)
    res = await session.execute(
        select(func.count(ReferralStats.id))
        .where(ReferralStats.referrer_id == user_id)
        .where(ReferralStats.level == level)
    )
    return res.scalar_one()


@router.callback_query(F.data == "referrals")
async def show_referrals(cb: CallbackQuery, session: AsyncSession):
    res = await session.execute(select(User).where(User.telegram_id == cb.from_user.id))
    user = res.scalar_one_or_none()

    if not user:
        await cb.answer("Сначала /start", show_alert=True)
        return

    # Считаем количество рефералов по уровням из таблицы связей
    level1_count = await count_referrals_by_level(session, user.id, 1)
    level2_count = await count_referrals_by_level(session, user.id, 2)
    level3_count = await count_referrals_by_level(session, user.id, 3)

    # Считаем заработанное (если есть транзакции типа REF_REWARD)
    # Если транзакций нет, будет 0.
    # Можно усложнить и считать отдельно по уровням, но пока покажем общую сумму за всё время.
    
    total_earnings_res = await session.execute(
        select(func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id)
        .where(Transaction.type == TransactionType.REF_REWARD)
    )
    total_earnings = total_earnings_res.scalar() or 0
    
    # "Выведено" считаем по транзакциям WITHDRAWAL
    withdrawn_res = await session.execute(
        select(func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id)
        .where(Transaction.type == TransactionType.WITHDRAWAL)
        .where(Transaction.status == "SUCCESS") # или Completed
    )
    withdrawn = withdrawn_res.scalar() or 0

    bot_username = (await cb.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user.referral_code}"

    text = (
        f"🎁 <b>Реферальная программа</b>\n\n"
        f"💰 Баланс: <b>{user.referral_balance} ₽</b>\n"
        f"💎 Всего заработано: <b>{total_earnings} ₽</b>\n"
        f"🏦 Выведено: <b>{withdrawn} ₽</b>\n\n"
        f"📊 <b>Ваша структура:</b>\n"
        f"1️⃣ Уровень (15%): <b>{level1_count}</b> чел.\n"
        f"2️⃣ Уровень (10%): <b>{level2_count}</b> чел.\n"
        f"3️⃣ Уровень (5%):  <b>{level3_count}</b> чел.\n\n"
        f"🔗 <b>Ваша ссылка для приглашения:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"Отправляйте ссылку друзьям и получайте % с их оплат!"
    )

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await cb.answer()


@router.message(Command("ref"))
async def cmd_ref(message: Message, session: AsyncSession):
    res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = res.scalar_one_or_none()

    if not user:
        await message.answer("Сначала /start")
        return

    bot_username = (await message.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user.referral_code}"

    await message.answer(
        f"🎁 Ваша реферальная ссылка:\n\n"
        f"<code>{ref_link}</code>\n\n"
        f"Приглашайте друзей и получайте:\n"
        f"• 15% от покупок уровня 1\n"
        f"• 10% от покупок уровня 2\n"
        f"• 5% от покупок уровня 3",
        parse_mode="HTML",
    )
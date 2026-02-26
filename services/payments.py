import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any


from aiogram import Bot
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from database.models import (
    User,
    Transaction,
    TransactionType,
    TransactionStatus,
    SubscriptionTier,
)
from utils.logger import logger


# Настраиваем планы по ТЗ
# Лимиты переводим в месячный запас токенов (из расчета 1 запрос = 1 токен)
# FREE: 10 в день (обрабатывается отдельно в scheduler)
# PREMIUM: 50 в день * 30 дней = 1500 токенов
# PREMIUM_X2: 100 в день * 30 дней = 3000 токенов

SUBSCRIPTION_PLANS = {
    SubscriptionTier.FREE:        {"price_rub": 0,    "tokens": 10,   "days": 0},
    SubscriptionTier.PREMIUM:     {"price_rub": 690,  "tokens": 1500, "days": 30},
    SubscriptionTier.PREMIUM_X2:  {"price_rub": 1090, "tokens": 3000, "days": 30},
}

# Пакеты (не являются подпиской, просто покупка токенов/генераций)
# Цены и количество токенов для пакетов (ID пакета -> {цена, токены})
# Предполагаем, что Video стоит 2 токена, Suno стоит 1 токен (по конфигу)
PACKETS = {
    "video_10":  {"price_rub": 290,  "tokens": 20,  "name": "Видео (10 ген)"},  # 10 * 2 = 20
    "video_50":  {"price_rub": 1290, "tokens": 100, "name": "Видео (50 ген)"}, # 50 * 2 = 100 (цена примерная!)
    "audio_20":  {"price_rub": 390,  "tokens": 20,  "name": "Suno (20 ген)"},  # 20 * 1 = 20
    "audio_100": {"price_rub": 1590, "tokens": 100, "name": "Suno (100 ген)"}, # 100 * 1 = 100 (цена примерная!)
}


async def create_pending_transaction(
    session: AsyncSession,
    user_id: int,
    amount: Decimal,
    currency: str,
    tx_type: TransactionType,
    payment_system: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Transaction:
    tx = Transaction(
        user_id=user_id,
        amount=amount,
        currency=currency,
        type=tx_type,
        status=TransactionStatus.PENDING,
        payment_system=payment_system,
        payment_id=secrets.token_urlsafe(16),
        extra_data=extra_data or {},
        created_at=datetime.utcnow(),
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


async def activate_subscription(
    session: AsyncSession,
    user_id: int,
    tier: SubscriptionTier,
) -> None:
    plan = SUBSCRIPTION_PLANS[tier]
    res = await session.execute(select(User).where(User.id == user_id).with_for_update())
    user = res.scalar_one()


    # tier + срок
    user.subscription_tier = tier.value
    if plan["days"] > 0:
        now = datetime.utcnow()
        if user.subscription_expires_at and user.subscription_expires_at > now:
            user.subscription_expires_at = user.subscription_expires_at + timedelta(days=plan["days"])
        else:
            user.subscription_expires_at = now + timedelta(days=plan["days"])


    # Начисляем токены за подписку
    user.tokens_balance += int(plan["tokens"])
    # Ставим флаг премиума
    if tier in [SubscriptionTier.PREMIUM, SubscriptionTier.PREMIUM_X2]:
        user.is_premium = True


    await session.commit()


async def activate_packet(
    session: AsyncSession,
    user_id: int,
    packet_id: str,
) -> None:
    """Активация разового пакета"""
    packet = PACKETS.get(packet_id)
    if not packet:
        return

    res = await session.execute(select(User).where(User.id == user_id).with_for_update())
    user = res.scalar_one()
    
    user.tokens_balance += int(packet["tokens"])
    await session.commit()


async def process_referral_rewards(session: AsyncSession, user_id: int, amount_rub: Decimal) -> None:
    """
    Level 1: 15%, Level 2: 10%, Level 3: 5%
    """
    res = await session.execute(select(User).where(User.id == user_id))
    user = res.scalar_one()


    # Level 1
    if user.referrer_id:
        res1 = await session.execute(select(User).where(User.id == user.referrer_id).with_for_update())
        ref1 = res1.scalar_one()
        ref1.referral_balance += (amount_rub * Decimal("0.15"))


        # Level 2
        if ref1.referrer_id:
            res2 = await session.execute(select(User).where(User.id == ref1.referrer_id).with_for_update())
            ref2 = res2.scalar_one()
            ref2.referral_balance += (amount_rub * Decimal("0.10"))


            # Level 3
            if ref2.referrer_id:
                res3 = await session.execute(select(User).where(User.id == ref2.referrer_id).with_for_update())
                ref3 = res3.scalar_one()
                ref3.referral_balance += (amount_rub * Decimal("0.05"))


    await session.commit()


# ----------------------------
# Telegram Stars
# ----------------------------
async def send_stars_invoice(
    bot: Bot,
    session: AsyncSession,
    chat_id: int,
    telegram_user_id: int,
    item_type: str, # 'tier' or 'packet'
    item_id: str,   # 'PREMIUM' or 'video_10'
) -> Message:
    res = await session.execute(select(User).where(User.telegram_id == telegram_user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise RuntimeError("User not found")

    price_rub = 0
    title = ""
    description = ""
    tokens = 0
    
    if item_type == "tier":
        tier = SubscriptionTier(item_id)
        plan = SUBSCRIPTION_PLANS[tier]
        price_rub = plan["price_rub"]
        title = f"Подписка {tier.value}"
        tokens = plan["tokens"]
        description = f"Лимит ~{int(tokens/30)} запросов/день.\nСрок: 30 дней."
        
    elif item_type == "packet":
        packet = PACKETS.get(item_id)
        if not packet:
            raise ValueError("Пакет не найден")
        price_rub = packet["price_rub"]
        title = packet["name"]
        tokens = packet["tokens"]
        description = f"Дополнительные {tokens} токенов (бессрочно)."

    stars_amount = int(price_rub) # 1 RUB = 1 XTR (пока так)
    if stars_amount <= 0:
        raise ValueError("Цена должна быть > 0")

    tx = await create_pending_transaction(
        session=session,
        user_id=user.id,
        amount=Decimal(price_rub),
        currency="XTR",
        tx_type=TransactionType.SUBSCRIPTION if item_type == "tier" else TransactionType.TOKEN_PURCHASE,
        payment_system="stars",
        extra_data={"item_type": item_type, "item_id": item_id, "tokens": tokens},
    )

    prices = [LabeledPrice(label=title, amount=stars_amount)]

    return await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=f"sub:{tx.payment_id}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )


async def handle_pre_checkout(pre_checkout: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)


async def handle_successful_payment(
    session: AsyncSession,
    telegram_user_id: int,
    payload: str,
    total_amount: int,
    currency: str,
) -> None:
    if not payload.startswith("sub:"):
        return

    payment_id = payload.split(":", 1)[1]
    tx_res = await session.execute(
        select(Transaction).where(Transaction.payment_id == payment_id).with_for_update()
    )
    tx = tx_res.scalar_one_or_none()
    if not tx or tx.status == TransactionStatus.SUCCESS:
        return

    tx.status = TransactionStatus.SUCCESS
    tx.completed_at = datetime.utcnow()
    await session.commit()

    item_type = tx.extra_data.get("item_type")
    item_id = tx.extra_data.get("item_id")
    
    if item_type == "tier":
        await activate_subscription(session, tx.user_id, SubscriptionTier(item_id))
    elif item_type == "packet":
        await activate_packet(session, tx.user_id, item_id)

    await process_referral_rewards(session, tx.user_id, Decimal(tx.amount))
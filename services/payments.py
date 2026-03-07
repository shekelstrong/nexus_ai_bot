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

# Импортируем конфигурацию тарифов и пакетов
from config import SUBSCRIPTION_TIERS, TOKEN_PACKAGES, VIDEO_PACKAGES


# Настраиваем планы согласно ТЗ
# FREE: 10 токенов в день (сбрасываются ежедневно в scheduler)
# Платные тарифы: токены начисляются на месяц

SUBSCRIPTION_PLANS = {
    SubscriptionTier.FREE:   {"price_rub": 0,    "tokens": 10,   "days": 0},
    SubscriptionTier.BASIC:  {"price_rub": 790,  "tokens": 460,  "days": 30},
    SubscriptionTier.PRO:    {"price_rub": 1490, "tokens": 880,  "days": 30},
    SubscriptionTier.VIP:    {"price_rub": 2490, "tokens": 1700, "days": 30},
    SubscriptionTier.ELITE:  {"price_rub": 3690, "tokens": 2600, "days": 30},
}

# Пакеты докупки токенов (бессрочные)
PACKETS = {
    "tokens_25":  {"price_rub": 390,  "tokens": 25,   "type": "tokens", "name": "🪙 25 токенов"},
    "tokens_50":  {"price_rub": 590,  "tokens": 50,   "type": "tokens", "name": "🪙 50 токенов"},
    "tokens_100": {"price_rub": 1190, "tokens": 100,  "type": "tokens", "name": "🪙 100 токенов"},
    # Видео-пакеты (отдельный тип)
    "video_10":  {"price_rub": 590,  "generations": 10, "type": "video", "name": "🎬 10 видео"},
    "video_25":  {"price_rub": 1190, "generations": 25, "type": "video", "name": "🎬 25 видео"},
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

    # Устанавливаем tier и срок действия
    user.subscription_tier = tier.value
    if plan["days"] > 0:
        now = datetime.utcnow()
        if user.subscription_expires_at and user.subscription_expires_at > now:
            user.subscription_expires_at = user.subscription_expires_at + timedelta(days=plan["days"])
        else:
            user.subscription_expires_at = now + timedelta(days=plan["days"])

    # Начисляем токены за подписку
    user.tokens_balance += int(plan["tokens"])
    
    # Для FREE тарифа ставим флаг is_premium = False
    # Для платных тарифов ставим is_premium = True
    user.is_premium = tier != SubscriptionTier.FREE

    await session.commit()


async def activate_packet(
    session: AsyncSession,
    user_id: int,
    packet_id: str,
) -> None:
    """Активация разового пакета (токены или видео)"""
    packet = PACKETS.get(packet_id)
    if not packet:
        logger.error(f"Packet not found: {packet_id}")
        return

    res = await session.execute(select(User).where(User.id == user_id).with_for_update())
    user = res.scalar_one()

    # В зависимости от типа пакета начисляем токены или видео-генерации
    if packet.get("type") == "video":
        user.video_generations_balance += int(packet.get("generations", 0))
    else:
        # По умолчанию считаем что это токены
        user.tokens_balance += int(packet.get("tokens", 0))
    
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
    item_type: str, # 'tier', 'tokens', or 'video'
    item_id: str,   # 'BASIC' or 'tokens_25' or 'video_10'
) -> Message:
    res = await session.execute(select(User).where(User.telegram_id == telegram_user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise RuntimeError("User not found")

    price_rub = 0
    title = ""
    description = ""
    tokens = 0
    video_gens = 0

    if item_type == "tier":
        tier = SubscriptionTier(item_id)
        plan = SUBSCRIPTION_PLANS[tier]
        price_rub = plan["price_rub"]
        title = f"Подписка {tier.value}"
        tokens = plan["tokens"]
        daily_tokens = tokens // 30 if tokens > 0 else 0
        description = f"Лимит ~{daily_tokens} токенов/день.\nСрок: 30 дней."

    elif item_type == "tokens":
        packet = PACKETS.get(item_id)
        if not packet:
            raise ValueError("Пакет токенов не найден")
        price_rub = packet["price_rub"]
        title = packet["name"]
        tokens = packet.get("tokens", 0)
        description = f"Дополнительные {tokens} токенов (бессрочно)."

    elif item_type == "video":
        packet = PACKETS.get(item_id)
        if not packet:
            raise ValueError("Видео-пакет не найден")
        price_rub = packet["price_rub"]
        title = packet["name"]
        video_gens = packet.get("generations", 0)
        description = f"Дополнительные {video_gens} генераций видео (бессрочно)."

    else:
        raise ValueError(f"Неизвестный тип оплаты: {item_type}")

    stars_amount = int(price_rub) # 1 RUB = 1 XTR
    if stars_amount <= 0 and item_type != "tier":
        raise ValueError("Цена должна быть > 0")

    tx_type = TransactionType.SUBSCRIPTION if item_type == "tier" else TransactionType.TOKEN_PURCHASE
    
    tx = await create_pending_transaction(
        session=session,
        user_id=user.id,
        amount=Decimal(price_rub),
        currency="XTR",
        tx_type=tx_type,
        payment_system="stars",
        extra_data={
            "item_type": item_type,
            "item_id": item_id,
            "tokens": tokens,
            "video_generations": video_gens
        },
    )

    prices = [LabeledPrice(label=title, amount=stars_amount)] if stars_amount > 0 else [LabeledPrice(label=title, amount=1)]

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
    elif item_type == "tokens":
        await activate_packet(session, tx.user_id, item_id)
    elif item_type == "video":
        await activate_packet(session, tx.user_id, item_id)

    await process_referral_rewards(session, tx.user_id, Decimal(tx.amount))
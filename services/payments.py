import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

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
from config import SUBSCRIPTION_TIERS, TOKEN_PACKAGES, REF_LEVELS, ADMIN_IDS

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
    "tokens_50":   {"price_rub": 150,  "tokens": 50,   "type": "tokens", "name": "🪙 50 токенов"},
    "tokens_100":  {"price_rub": 250,  "tokens": 100,  "type": "tokens", "name": "🪙 100 токенов"},
    "tokens_300":  {"price_rub": 750,  "tokens": 300,  "type": "tokens", "name": "🪙 300 токенов"},
    "tokens_500":  {"price_rub": 1150, "tokens": 500,  "type": "tokens", "name": "🪙 500 токенов"},
    "tokens_1000": {"price_rub": 1950, "tokens": 1000, "type": "tokens", "name": "🪙 1000 токенов"},
    "tokens_2500": {"price_rub": 3750, "tokens": 2500, "type": "tokens", "name": "🪙 2500 токенов"},
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
    """Активация разового пакета токенов"""
    packet = PACKETS.get(packet_id)
    if not packet:
        logger.error(f"Packet not found: {packet_id}")
        return

    res = await session.execute(select(User).where(User.id == user_id).with_for_update())
    user = res.scalar_one()

    # Начисляем токены
    user.tokens_balance += int(packet.get("tokens", 0))
    
    await session.commit()


async def get_referrer_chain(session: AsyncSession, user_id: int, max_depth: int = 3) -> List[Dict]:
    """
    Возвращает цепочку рефералов до 3 уровня.
    
    Returns:
        List[Dict]: [{'user': User, 'level': 1, 'bonus_percent': 0.15}, ...]
    """
    chain = []
    current_user_id = user_id

    for level in range(1, max_depth + 1):
        res = await session.execute(
            select(User).where(User.id == current_user_id)
        )
        current_user = res.scalar_one_or_none()
        
        if not current_user or not current_user.referrer_id:
            break
        
        # Получаем реферера
        referrer_res = await session.execute(
            select(User).where(User.id == current_user.referrer_id)
        )
        referrer = referrer_res.scalar_one_or_none()
        
        if not referrer:
            break
        
        bonus_percent = REF_LEVELS[level - 1] if level <= len(REF_LEVELS) else 0
        
        chain.append({
            'user': referrer,
            'level': level,
            'bonus_percent': bonus_percent,
        })
        
        current_user_id = referrer.id

    return chain


async def process_referral_rewards(
    session: AsyncSession,
    user_id: int,
    amount_rub: Decimal,
    notify_callback=None
) -> Dict:
    """
    Начисление реферальных бонусов (3 уровня: 15%/10%/5%).
    
    Args:
        session: DB сессия
        user_id: ID пользователя, который совершил платеж
        amount_rub: Сумма платежа в рублях
        notify_callback: Функция для отправки уведомлений (бот, referrer, bonus)
    
    Returns:
        Dict: {'total_bonus': Decimal, 'referrers': [...]}
    """
    chain = await get_referrer_chain(session, user_id)
    
    total_bonus = Decimal("0")
    referrer_info = []

    for ref_data in chain:
        referrer = ref_data['user']
        level = ref_data['level']
        bonus_percent = ref_data['bonus_percent']
        
        bonus = amount_rub * Decimal(str(bonus_percent))
        total_bonus += bonus
        
        # Начисляем бонус на реферальный баланс
        referrer.referral_balance += bonus
        
        referrer_info.append({
            'telegram_id': referrer.telegram_id,
            'username': referrer.username,
            'level': level,
            'bonus': bonus,
        })
        
        # Уведомляем реферера
        if notify_callback:
            await notify_callback(referrer.telegram_id, level, bonus)

    await session.commit()
    
    return {
        'total_bonus': total_bonus,
        'referrers': referrer_info,
    }


async def process_platega_payment(
    session: AsyncSession,
    order_id: int,
    amount_rub: Decimal,
    notify_callback=None
) -> bool:
    """
    Обработка успешного платежа от Platega.
    
    Args:
        session: DB сессия
        order_id: ID заказа (содержит тип и ID пакета)
        amount_rub: Сумма платежа
        notify_callback: Функция для уведомлений
    
    Returns:
        bool: True если успешно
    """
    # Парсим order_id: format "tokens_25_12345" или "tier_BASIC_12345"
    parts = str(order_id).split("_")
    
    if len(parts) < 3:
        logger.error(f"Invalid order_id format: {order_id}")
        return False
    
    item_type = parts[0]  # tokens, tier
    user_telegram_id = int(parts[-1])  # Последний элемент - telegram_id
    
    if len(parts) == 3:
        # tokens_50_12345 → item_id=tokens_50; tier_BASIC_12345 → item_id=BASIC
        if item_type == "tokens":
            item_id = f"{parts[0]}_{parts[1]}"
        else:
            item_id = parts[1]
    else:
        item_id = "_".join(parts[1:-1])
    
    # Находим пользователя
    res = await session.execute(select(User).where(User.telegram_id == user_telegram_id))
    user = res.scalar_one_or_none()
    
    if not user:
        logger.error(f"User not found: {user_telegram_id}")
        return False
    
    # Находим транзакцию
    tx_res = await session.execute(
        select(Transaction).where(
            Transaction.payment_id == str(order_id),
            Transaction.status == TransactionStatus.PENDING
        )
    )
    tx = tx_res.scalar_one_or_none()
    
    if not tx:
        # Создаем новую транзакцию если не найдена
        tx = await create_pending_transaction(
            session=session,
            user_id=user.id,
            amount=amount_rub,
            currency="RUB",
            tx_type=TransactionType.TOKEN_PURCHASE,
            payment_system="platega",
            extra_data={"item_type": item_type, "item_id": item_id},
        )
    
    # Обновляем транзакцию
    tx.status = TransactionStatus.SUCCESS
    tx.completed_at = datetime.utcnow()
    await session.commit()
    
    # Активируем товар
    tokens_added = 0
    
    if item_type == "tier":
        tier = SubscriptionTier(item_id.upper())
        plan = SUBSCRIPTION_PLANS[tier]
        tokens_added = plan["tokens"]
        await activate_subscription(session, user.id, tier)
        
    elif item_type == "tokens":
        packet = PACKETS.get(item_id)
        if packet:
            tokens_added = packet.get("tokens", 0)
            await activate_packet(session, user.id, item_id)
            
    # Обрабатываем реферальные начисления (15%/10%/5%)
    referrer_result = await process_referral_rewards(
        session, user.id, amount_rub, notify_callback
    )
    
    logger.info(
        f"✅ Platega payment: User {user_telegram_id} +{tokens_added} tokens | "
        f"Amount: {amount_rub} RUB | "
        f"Ref bonus: {referrer_result['total_bonus']} RUB"
    )
    
    return True


async def get_purchase_details(item_type: str, item_id: str) -> Dict:
    """
    Возвращает детали покупки для отображения пользователю.
    
    Returns:
        Dict: {'tokens': int, 'duration_days': int}
    """
    result = {'tokens': 0, 'duration_days': 0}
    
    if item_type == "tier":
        tier = SubscriptionTier(item_id.upper())
        plan = SUBSCRIPTION_PLANS.get(tier)
        if plan:
            result['tokens'] = plan['tokens']
            result['duration_days'] = plan['days']
            
    elif item_type == "tokens":
        packet = PACKETS.get(item_id)
        if packet:
            result['tokens'] = packet.get('tokens', 0)
            result['duration_days'] = 0  # Бессрочно
            
    return result
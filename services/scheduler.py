import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, update
from database.session import async_session_maker
from database.models import User, SubscriptionTier
from utils.logger import logger
from config import SUBSCRIPTION_TIERS

async def reset_free_tokens():
    """Сбрасывает токены до лимита для пользователей на тарифе FREE."""
    try:
        async with async_session_maker() as session:
            free_limit = SUBSCRIPTION_TIERS["FREE"]["tokens"]
            
            # ИСПРАВЛЕНИЕ: Добавлено условие tokens_balance < free_limit
            # Теперь купленные или выданные админом токены не сгорают!
            result = await session.execute(
                update(User)
                .where(User.subscription_tier == SubscriptionTier.FREE.value)
                .where(User.tokens_balance < free_limit)
                .values(tokens_balance=free_limit)
            )
            await session.commit()
            logger.info(f"✅ Ежедневный сброс токенов выполнен. Обновлено пользователей: {result.rowcount}.")
    except Exception as e:
        logger.error(f"❌ Ошибка при сбросе токенов: {e}")

async def daily_token_reset_task():
    """Фоновая задача для ежедневного сброса токенов (в полночь по серверному времени)."""
    logger.info("⏳ Планировщик сброса токенов запущен.")
    while True:
        now = datetime.utcnow()
        # Вычисляем время до следующей полуночи
        next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        sleep_seconds = (next_midnight - now).total_seconds()
        
        logger.info(f"⏳ Планировщик токенов ждет {sleep_seconds:.0f} секунд до полуночи.")
        await asyncio.sleep(sleep_seconds)
        
        # Наступила полночь - сбрасываем токены
        await reset_free_tokens()

async def subscription_expiration_task():
    """Фоновая задача для проверки истекших подписок."""
    logger.info("⏳ Планировщик проверки подписок запущен.")
    while True:
        try:
            async with async_session_maker() as session:
                now = datetime.utcnow()
                # Ищем пользователей с истекшей подпиской
                result = await session.execute(
                    select(User).where(
                        (User.subscription_expires_at <= now) &
                        (User.subscription_tier != SubscriptionTier.FREE.value)
                    )
                )
                expired_users = result.scalars().all()
                
                for user in expired_users:
                    logger.info(f"🔻 Подписка истекла у пользователя {user.telegram_id}")
                    user.subscription_tier = SubscriptionTier.FREE.value
                    user.is_premium = False
                    # Сбрасываем токены до базового тарифа FREE только если их меньше
                    if user.tokens_balance < SUBSCRIPTION_TIERS["FREE"]["tokens"]:
                        user.tokens_balance = SUBSCRIPTION_TIERS["FREE"]["tokens"]
                
                if expired_users:
                    await session.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка в проверке подписок: {e}")
        
        # Проверяем раз в час
        await asyncio.sleep(3600)
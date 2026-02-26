import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import async_session_maker
from database.models import User, SubscriptionTier
from utils.logger import logger


async def daily_token_reset_task():
    """
    Фоновая задача: каждый час проверяет FREE-юзеров,
    у которых daily_tokens_reset_at <= now.
    Обнуляет токены до 10 и переносит reset на +24ч.
    """
    while True:
        try:
            async with async_session_maker() as session:
                now = datetime.utcnow()

                # Найти FREE-юзеров, которым пора сбросить
                result = await session.execute(
                    select(User).where(
                        User.subscription_tier == SubscriptionTier.FREE,
                        User.daily_tokens_reset_at <= now,
                    )
                )
                users = result.scalars().all()

                for user in users:
                    user.tokens_balance = 10
                    user.daily_tokens_reset_at = now + timedelta(days=1)

                if users:
                    await session.commit()
                    logger.info(f"Daily token reset: {len(users)} users")

        except Exception as e:
            logger.exception("Error in daily_token_reset_task")

        await asyncio.sleep(3600)  # каждый час


async def subscription_expiration_task():
    """
    Опционально: проверяет истёкшие подписки и откатывает на FREE
    """
    while True:
        try:
            async with async_session_maker() as session:
                now = datetime.utcnow()

                result = await session.execute(
                    select(User).where(
                        User.subscription_tier != SubscriptionTier.FREE,
                        User.subscription_expires_at <= now,
                    )
                )
                users = result.scalars().all()

                for user in users:
                    logger.info(f"Subscription expired for user {user.telegram_id}, rolling back to FREE")
                    user.subscription_tier = SubscriptionTier.FREE
                    user.subscription_expires_at = None
                    # Токены не трогаем (могут быть уже потрачены)

                if users:
                    await session.commit()
                    logger.info(f"Subscription expiration: {len(users)} users")

        except Exception as e:
            logger.exception("Error in subscription_expiration_task")

        await asyncio.sleep(3600)
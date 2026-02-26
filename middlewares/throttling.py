import time
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis

from database.models import SubscriptionTier


class ThrottlingMiddleware(BaseMiddleware):
    """
    Flood control (пример):
      - 5 сообщений/сек на пользователя
      - BASIC: 30 запросов/час
      - PRO+: без лимита по часу (но flood control остаётся)
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        db_user = data.get("db_user")
        tier = db_user.subscription_tier if db_user else SubscriptionTier.FREE

        # 1) Flood control: 5 msg/sec
        key_flood = f"flood:{user.id}:{int(time.time())}"
        cnt = await self.redis.incr(key_flood)
        if cnt == 1:
            await self.redis.expire(key_flood, 2)
        if cnt > 5:
            # молча дропаем / можно показать предупреждение раз в N секунд
            return

        # 2) Hourly лимит только для BASIC (пример)
        if tier == SubscriptionTier.BASIC:
            key_hour = f"rl:basic:{user.id}:{int(time.time() // 3600)}"
            hcnt = await self.redis.incr(key_hour)
            if hcnt == 1:
                await self.redis.expire(key_hour, 3700)
            if hcnt > 30:
                if getattr(event, "message", None):
                    await event.message.answer("⏳ Лимит: 30 запросов/час для BASIC. Попробуйте позже.")
                return

        return await handler(event, data)
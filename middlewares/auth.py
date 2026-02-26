from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class AuthMiddleware(BaseMiddleware):
    """
    - Проверяет, что пользователь зарегистрирован (есть в БД)
    - Проверяет бан
    - Если не зарегистрирован — просит /start
    """

    async def __call__(self, handler, event: TelegramObject, data: dict):
        session: AsyncSession = data.get("session")
        user = data.get("event_from_user")

        if not session or not user:
            return await handler(event, data)

        res = await session.execute(select(User).where(User.telegram_id == user.id))
        db_user = res.scalar_one_or_none()

        if not db_user:
            # разрешаем только /start и некоторые service events
            text = getattr(getattr(event, "message", None), "text", None)
            if not text or not text.startswith("/start"):
                if getattr(event, "message", None):
                    await event.message.answer("Сначала нажмите /start для регистрации.")
                return
            return await handler(event, data)

        if db_user.is_banned:
            if getattr(event, "message", None):
                await event.message.answer("Доступ ограничен.")
            return

        data["db_user"] = db_user
        return await handler(event, data)
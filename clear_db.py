import asyncio
from sqlalchemy import select, delete
from database.session import async_session_maker
from database.models import User
from config import ADMIN_IDS

async def clear_db():
    async with async_session_maker() as session:
        result = await session.execute (
            delete(User) .where (
                User.telegram_id.not_in(ADMIN_IDS)
            )
        )
        await session.commit()
        print(f"✅ Удалено {result.rowcount} пользователей")
        print(f"Администраторы сохранены: {ADMIN_IDS}")

asyncio.run(clear_db())

# bot.py
import asyncio
import json
import re

# 👇 САМОЕ ПЕРВОЕ — настройка логирования (до импортов библиотек!)
from utils.logger import setup_logger
logger = setup_logger()

# Теперь импорты библиотек
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import (
    settings,
    BOT_TOKEN, TARIFFS, REF_LEVELS, ADMIN_IDS
)
from database.db import db

# ИМПОРТ MIDDLEWARE (Используем твой файл database.py)
from middlewares.database import DbSessionMiddleware

# Импорт роутеров
from handlers import user 
from handlers.admin import admin_panel 
from handlers.generation import selection, process 

# ❌ УДАЛИ ЭТИ СТРОКИ (старая настройка логирования)
# logging.basicConfig(level=logging.INFO)
# logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
# logging.getLogger("aiogram.event").setLevel(logging.ERROR)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

async def on_startup(bot: Bot):
    await db.connect()
    # Удаляем вебхук для поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    logger.info(f"✅ Bot started in POLLING mode: @{me.username}")

async def main():
    # --- РЕГИСТРАЦИЯ MIDDLEWARE ---
    # Это самое важное! Без этого будет ошибка "missing session"
    dp.update.middleware(DbSessionMiddleware(session_pool=db.session_maker))

    # Если хочешь включить AuthMiddleware, его нужно добавить ПОСЛЕ DbSessionMiddleware
    # from middlewares.auth import AuthMiddleware
    # dp.message.middleware(AuthMiddleware()) 
    # (Пока давай запустим хотя бы базу, чтобы работало /start)

    # --- РОУТЕРЫ ---
    dp.include_router(admin_panel.router)
    dp.include_router(selection.router)
    dp.include_router(user.router)
    dp.include_router(process.router)

    dp.startup.register(on_startup)

    # ЗАПУСК
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
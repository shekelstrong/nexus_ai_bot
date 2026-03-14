import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

# Импорт настроек и логгера
from utils.logger import setup_logger
logger = setup_logger()

from config import (
    settings,
    BOT_TOKEN
)
from database.db import db

# Импорты Middleware и роутеров
from middlewares.database import DbSessionMiddleware
from handlers import user
from handlers.admin import admin_panel, notifications
from handlers.generation import selection, process

# Импорт вебхук сервера
from services.webhook_server import webhook_server
# Импорт фоновых задач (планировщика)
from services.scheduler import daily_token_reset_task, subscription_expiration_task

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- СУПЕР-ДЕБАГ ХЕНДЛЕР ---
# Этот хендлер поймает ЛЮБОЕ обновление до того, как оно уйдет в роутеры
@dp.update()
async def debug_handler(update: types.Update):
    # Мы увидим это в logs/bot.log или через journalctl
    logger.info(f"🔍 ДЕБАГ: Пришло обновление ID={update.update_id}")
    if update.message:
        logger.info(f"📩 Текст сообщения: {update.message.text} от {update.message.from_user.id}")
    return False  # Позволяет событию идти дальше к роутерам

async def on_startup(bot: Bot):
    # Подключаем БД
    await db.connect()
    # Принудительно очищаем вебхуки для работы Polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Настройка меню команд
    await bot.set_my_commands([
        BotCommand(command="start", description="Перезагрузка бота"),
        BotCommand(command="account", description="Мой профиль"),
        BotCommand(command="photo", description="Создать изображение"),
        BotCommand(command="nanobanana", description="Nano Banana"),
        BotCommand(command="s", description="Интернет поиск"),
        BotCommand(command="privacy", description="Соглашения"),
        BotCommand(command="earn", description="Рефералка")
    ])
    
    me = await bot.get_me()
    logger.info(f"✅ Bot started in POLLING mode: @{me.username}")
    
    # Запускаем вебхук сервер для Platega
    await webhook_server.start(bot)
    
    # Запуск фоновых задач (планировщик для сброса токенов и подписок)
    asyncio.create_task(daily_token_reset_task())
    asyncio.create_task(subscription_expiration_task())

async def main():
    # 1. Регистрация Middleware (БД обязательна для работы роутеров)
    dp.update.middleware(DbSessionMiddleware(session_pool=db.session_maker))

    # 2. Регистрация роутеров
    dp.include_router(admin_panel.router)
    dp.include_router(selection.router)
    dp.include_router(user.router)  # Тут лежит наш /start (включает payment)
    dp.include_router(process.router)

    # Регистрация функции старта
    dp.startup.register(on_startup)
    
    # Регистрация функции остановки (для корректного закрытия вебхук сервера)
    @dp.shutdown()
    async def on_shutdown(bot: Bot):
        logger.info("Bot shutting down...")
        await webhook_server.stop(None)

    # 3. Запуск прослушки
    logger.info("🚀 Запуск polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
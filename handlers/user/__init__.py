from aiogram import Router
from . import start, profile, payment, referrals, share

# Создаем общий роутер для пользователя
router = Router(name="user_main_router")

# Подключаем модули
router.include_router(start.router)
router.include_router(profile.router)
router.include_router(payment.router)
router.include_router(referrals.router)
router.include_router(share.router)

# Экспортируем router, чтобы его увидел bot.py
__all__ = ["router", "start", "profile", "payment", "referrals", "share"]
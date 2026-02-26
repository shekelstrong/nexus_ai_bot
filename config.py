import os
from typing import List, Optional, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

# --- PYDANTIC SETTINGS ---
class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: str = "0"
    
    # DB
    DATABASE_URL: str = "sqlite+aiosqlite:///nexus.db"
    ENVIRONMENT: str = "production" # development / production

    # API Keys
    OPENROUTER_API_KEY: str
    FAL_AI_API_KEY: str

    # Webhook
    BASE_URL: str = "https://your-domain.com"
    WEB_PORT: int = 8443
    WEBHOOK_PATH: str = "/webhook/telegram"
    WEBHOOK_URL: str = ""
    
    # Payments
    PLATEGA_MERCHANT_ID: Optional[str] = None
    PLATEGA_SECRET: Optional[str] = None
    
    # Extra (на всякий случай, если где-то используется)
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_ids_list(self) -> List[int]:
        if not self.ADMIN_IDS: return []
        try:
            return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip().isdigit()]
        except: return []

settings = Settings()

# --- ЭКСПОРТ КОНСТАНТ (Для совместимости со старым кодом) ---
BOT_TOKEN = settings.BOT_TOKEN
ADMIN_IDS = settings.admin_ids_list
DATABASE_URL = settings.DATABASE_URL
ENVIRONMENT = settings.ENVIRONMENT

BASE_URL = settings.BASE_URL
WEB_PORT = settings.WEB_PORT
WEBHOOK_PATH = settings.WEBHOOK_PATH
WEBHOOK_URL = settings.WEBHOOK_URL
PLATEGA_WEBHOOK_PATH = "/webhook/platega"
PLATEGA_MERCHANT_ID = settings.PLATEGA_MERCHANT_ID
PLATEGA_SECRET = settings.PLATEGA_SECRET

OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
FAL_AI_API_KEY = settings.FAL_AI_API_KEY

SSL_CERT_PATH = settings.SSL_CERT_PATH
SSL_KEY_PATH = settings.SSL_KEY_PATH

# --- ЛОГИЧЕСКИЕ КОНСТАНТЫ ---
TARIFFS = {
    "day": {"price": 100, "gens": 10, "name": "🚀 Тест-драйв (10 шт)"},
    "week": {"price": 450, "gens": 50, "name": "📅 Неделька (50 шт)"},
    "month": {"price": 1600, "gens": 200, "name": "🗓 Месяц (200 шт)"},
    "month3": {"price": 7000, "gens": 1000, "name": "🔥 3 Месяца (1000 шт)"},
    "month6": {"price": 18000, "gens": 3000, "name": "💎 Полгода (3000 шт)"},
    "year": {"price": 50000, "gens": 10000, "name": "👑 Год PRO MAX (10000 шт)"}
}

REF_LEVELS = [0.15, 0.10, 0.05]

TEXTS = {
    "ru": {
        "welcome": "👋 <b>Добро пожаловать в Nexus AI!</b>\n\n🍌 <b>Free</b> — Лимитировано\n💎 <b>PRO</b> — Премиум качество без очередей\n\nВыберите модель или категорию:",
        "sub_lock": "🔒 <b>Доступ закрыт!</b>\nПодпишись:",
        "sub_btn": "✅ Я подписался",
        "sub_no": "❌ Ты еще не подписался!",
        "sub_ok": "✅ Доступ открыт!",
        "profile_full": "👤 <b>ID:</b> <code>{uid}</code>\n\n🍌 <b>Баланс:</b> {bal} шт.\n💳 <b>Руб. Баланс:</b> {rub}₽\n👥 <b>Приглашено:</b> {refs} чел.\n\n🔗 <b>Реф. ссылка:</b>\n<code>{link}</code>",
        "bonus_ok": "🎁 <b>Ежедневный бонус!</b>\n+1 банан начислен.",
        "bonus_wait": "⏳ Бонус уже получен.\nДо следующего: <b>{h}ч {m}м</b>",
        "gen_wait": "⏳ Генерирую...",
        "low_bal": "❌ <b>Мало бананов!</b>\nКупите пакет.",
        "err": "⚠️ Ошибка: {err}",
        "buy_menu": "💎 <b>Тарифы Nexus AI</b>",
        "buy_desc": "Вы выбрали: <b>{name}</b>\nЦена: <b>{price}₽</b>"
    }
}

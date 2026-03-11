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
    PLATEGA_TOKEN: Optional[str] = None

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
PLATEGA_TOKEN = settings.PLATEGA_TOKEN

OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
FAL_AI_API_KEY = settings.FAL_AI_API_KEY

SSL_CERT_PATH = settings.SSL_CERT_PATH
SSL_KEY_PATH = settings.SSL_KEY_PATH

# --- ЛОГИЧЕСКИЕ КОНСТАНТЫ ---
# Тарифные планы (токены начисляются на месяц)
SUBSCRIPTION_TIERS = {
    "FREE":   {"price": 0,     "tokens": 10,   "days": 0,  "name": "🆓 FREE (10 токенов/день)"},
    "BASIC":  {"price": 790,   "tokens": 460,  "days": 30, "name": "📦 BASIC (460 токенов/месяц)"},
    "PRO":    {"price": 1490,  "tokens": 880,  "days": 30, "name": "⭐ PRO (880 токенов/месяц)"},
    "VIP":    {"price": 2490,  "tokens": 1700, "days": 30, "name": "🏆 VIP (1700 токенов/месяц)"},
    "ELITE":  {"price": 3690,  "tokens": 2600, "days": 30, "name": "💎 ELITE (2600 токенов/месяц)"},
}

# Пакеты докупки токенов (бессрочные)
TOKEN_PACKAGES = {
    "tokens_25":  {"price": 390,  "tokens": 25,   "name": "🪙 25 токенов"},
    "tokens_50":  {"price": 590,  "tokens": 50,   "name": "🪙 50 токенов"},
    "tokens_100": {"price": 1190, "tokens": 100,  "name": "🪙 100 токенов"},
}

# Старые тарифы (для совместимости, будут удалены позже)
TARIFFS = SUBSCRIPTION_TIERS

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
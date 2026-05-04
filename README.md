<div align="center">

# 🧠 Nexus AI Bot

**Multi‑model Telegram AI bot** — generate text, images, and videos from a single chat interface.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.13-2BA4E0?logo=telegram&logoColor=white)](https://aiogram.dev)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-FCA121?logo=sqlalchemy&logoColor=white)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-Proprietary-8A2BE2)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/Powered_by-OpenRouter-FF6B6B)](https://openrouter.ai)
[![FAL AI](https://img.shields.io/badge/Powered_by-FAL_AI-00C7B7)](https://fal.ai)
[![Platega](https://img.shields.io/badge/Payments-Platega-4A90D9)](https://platega.com)

</div>

---

## 📋 About

Nexus AI Bot is a **feature‑rich Telegram bot** that brings multiple AI capabilities into a single conversational interface. Users can:

- Chat with state‑of‑the‑art **LLMs** (GPT‑5, Claude, Gemini, DeepSeek, Grok, etc.)
- Generate **images** from text prompts with 24 style presets
- Create **videos** from text, images, or motion reference
- Manage subscriptions and buy token packs via **Platega** payments
- Earn rewards through a **3‑level referral system**

The bot runs an **inline keyboard** interface in Russian (localized) and supports both polling and webhook modes for Telegram updates.

---

## ✨ Features

### 🤖 Text Generation
| Family | Models |
|--------|--------|
| **OpenAI** | GPT‑5, GPT‑5 Mini, GPT‑4o Mini |
| **Anthropic** | Claude Opus 4.5, Sonnet 4.5, Haiku 4.5 |
| **Google** | Gemini 2.5 Pro, 2.5 Flash, 2.0 Flash |
| **DeepSeek** | V3.2, R1 (reasoning) |
| **xAI** | Grok 4.1 Fast, Grok 4 Fast, Code Fast |
| **Alibaba** | Qwen3 Coder, Qwen3 235B |
| **Others** | Mistral Nemo, Kimi K2, Perplexity Sonar |

### 🎨 Image Generation
- **GPT‑5 Image** / **GPT‑5.4 Image 2** (OpenRouter, size picker with 1:1, 2:3, 3:2 presets)
- **Flux 2.0** (Pro, Max, Flex, Klein) — via FAL AI
- **Seedream 4.5** — by ByteDance
- **Nano Banana** — Gemini‑based exclusive model (Nano Banana, Pro, 2)
- **24 style presets** — Anime, Cyberpunk, GTA V, Minecraft, Pixar, Oil Painting, Vaporwave, Ukiyo‑e, and more
- **Image size selection** for GPT Image models

### 🎥 Video Generation
- **Text‑to‑video** — Kling 2.6, Veo 3.1
- **Image‑to‑video** — animate photos with Kling 2.6, Veo 3.1, Seedance 2.0
- **First‑last frame interpolation** — Veo 3.1 creates smooth transitions
- **Motion control** — Kling Motion transfers movement from video reference
- Duration options: 5 sec / 10 sec

### 🔍 Web Search
Built‑in AI‑powered search via **Perplexity Sonar** models with real‑time internet access and deep research capabilities.

### 💳 Payment & Monetization
- **Platega** payment gateway integration
- **5 subscription tiers**: FREE (daily tokens), BASIC, PRO, VIP, ELITE
- **6 token packs** (50–2500 tokens, one‑time purchase)
- Daily token resets for free tier
- Scheduler for subscription expiration checks

### 👥 Referral System
- **3‑level** referral rewards: 15% / 10% / 5%
- Unique referral links generated per user
- Referral balance tracking

### 🗄️ Data & Storage
- **SQLAlchemy 2.0** async ORM with PostgreSQL (SQLite fallback for dev)
- Alembic migrations
- Generation history, message history, templates
- Promo codes system
- Admin panel with broadcast notification support

---

## 🏗️ Architecture

```
nexus_ai_bot/
├── bot.py                  # Entry point — Aiogram dispatcher, middleware, router registration
├── config.py               # Pydantic Settings + subscription/package configs
├── model_config.py         # Model catalog (text, image, video, search)
│
├── handlers/
│   ├── user/               # /start, /account, payments, referrals, profile
│   ├── generation/         # Model selection, prompt handling, generation process
│   └── admin/              # Admin panel, notification broadcasting
│
├── services/
│   ├── providers/          # API providers: OpenRouter, FAL AI
│   ├── generators/         # Standard text/image, Kling, Veo, Wan, Seedream, FAL video
│   ├── api_client.py       # Unified API client facade
│   ├── fal_ai.py           # FAL AI file upload + request submission
│   ├── openrouter.py       # OpenRouter API calls
│   ├── payments.py         # Subscription & transaction logic
│   ├── platega_client.py   # Platega payment gateway integration
│   ├── webhook_server.py   # Webhook server for Platega callbacks
│   └── scheduler.py        # Daily token reset & subscription expiration tasks
│
├── database/
│   ├── models.py           # SQLAlchemy models: User, Generation, Transaction, etc.
│   ├── session.py          # Async session management
│   └── db.py               # Database connection pool
│
├── middlewares/
│   ├── database.py         # Injects AsyncSession into handler context
│   ├── auth.py             # Authentication checks
│   └── throttling.py       # Rate limiting
│
├── keyboards/
│   └── inline.py           # All inline keyboard builders
│
├── states/
│   └── generation_states.py  # FSM states for generation workflows
│
├── utils/
│   ├── logger.py           # Logging configuration
│   └── __init__.py
│
├── alembic/                # Database migrations
├── docker-compose.yml      # Bot + PostgreSQL + Redis
├── Dockerfile              # Python 3.11 slim container
└── requirements.txt
```

### Request Flow

```
User Message → Telegram API → Webhook/Polling → Aiogram Dispatcher
    → Middleware (DB session) → Router → Handler
        → Services (OpenRouter / FAL AI API)
            → External AI Provider
        → Response → Telegram API → User
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.11+ |
| **Bot Framework** | Aiogram 3.13 |
| **Database** | PostgreSQL 15 (primary), SQLite (dev fallback) |
| **ORM** | SQLAlchemy 2.0 + asyncpg |
| **Migrations** | Alembic |
| **Cache** | Redis 7 |
| **Text AI** | OpenRouter API (GPT, Claude, Gemini, DeepSeek, Grok, etc.) |
| **Image AI** | FAL AI API (Flux, Stable Diffusion), OpenRouter (GPT Image) |
| **Video AI** | FAL AI API (Kling, Veo, Seedance) |
| **Payments** | Platega |
| **Config** | Pydantic Settings + python-dotenv |
| **HTTP** | aiohttp, httpx |
| **Deployment** | Docker, Docker Compose |

---

## 🚀 Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15 (or SQLite for local dev)
- Redis 7
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenRouter API Key
- FAL AI API Key
- Platega Merchant credentials

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/shekelstrong/nexus_ai_bot.git
cd nexus_ai_bot

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file (see Configuration section)
cp .env.example .env

# 5. Run database migrations
alembic upgrade head

# 6. Start the bot
python bot.py
```

### Docker Deployment

```bash
docker compose up -d
```

---

## ⚙️ Configuration

All configuration is loaded from a `.env` file via `pydantic-settings`. Create a `.env` file in the project root:

```env
# Telegram
BOT_TOKEN=
ADMIN_IDS=            # Comma-separated Telegram user IDs

# Database
DATABASE_URL=         # Default: sqlite+aiosqlite:///nexus.db
ENVIRONMENT=          # development / production

# APIs
OPENROUTER_API_KEY=
FAL_AI_API_KEY=

# Webhook (required for Platega callbacks in production)
BASE_URL=
WEB_PORT=8443
WEBHOOK_PATH=/webhook/telegram

# Payments (Platega)
PLATEGA_MERCHANT_ID=
PLATEGA_TOKEN=

# SSL (optional)
SSL_CERT_PATH=
SSL_KEY_PATH=
```

> **Note**: Never commit your `.env` file. The `.gitignore` already excludes it.

---

## 📊 Database Models

| Model | Purpose |
|-------|---------|
| `User` | Telegram users, balances, subscription tier, referral info |
| `Generation` | Generation history (model, prompt, result, status, cost) |
| `Transaction` | Payment transactions (type, amount, status, payment system) |
| `MessageHistory` | Conversation history per user per model |
| `ReferralStats` | Referrer – referral relationships with levels |
| `Template` | Saved prompt templates per user |
| `PromoCode` | Promotional codes with token rewards |
| `SystemLog` | Application‑level logging |

---

## 🤝 Contributing

This is a proprietary project. For bug reports or feature requests, please open an [issue](https://github.com/shekelstrong/nexus_ai_bot/issues).

---

## 📄 License

Proprietary — all rights reserved.

---

<div align="center">
  <sub>Built with ❤️ for the Telegram community</sub>
</div>

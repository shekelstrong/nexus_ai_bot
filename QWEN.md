# Nexus AI Bot - Project Context

## Project Overview

**Nexus AI Bot** is a Telegram bot that provides AI-powered content generation services including text, images, video, and search capabilities. The bot integrates with multiple AI providers (OpenRouter, FAL AI) and offers a subscription-based economy with referral rewards.

### Key Features
- **Multi-modal generation**: Text, images, video, and search queries
- **50+ AI models** from providers: OpenAI, Anthropic, Google, DeepSeek, Meta, xAI, Mistral, and more
- **Token-based economy**: Users purchase generation credits via subscription tiers
- **Referral system**: 3-level referral rewards (15%, 10%, 5%)
- **Premium subscriptions**: FREE, PREMIUM, PREMIUM_X2 tiers
- **Payment integration**: Platega payment system
- **Message history**: Persistent conversation context with models

## Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | Python 3.11, aiogram 3.x (Telegram Bot API) |
| **Database** | PostgreSQL/SQLite with SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Caching** | Redis |
| **AI Providers** | OpenRouter API, FAL AI API |
| **Validation** | Pydantic Settings |
| **Deployment** | Docker, Docker Compose |

## Project Structure

```
nexus_ai_bot/
├── bot.py                 # Main entry point, bot initialization
├── config.py              # Settings, constants, tariffs, localized texts
├── model_config.py        # Model catalog (50+ models by category/family)
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker services (bot, postgres, redis)
├── Dockerfile             # Container build instructions
├── alembic.ini            # Database migration config
│
├── database/
│   ├── models.py          # SQLAlchemy models (User, Generation, Transaction, etc.)
│   ├── db.py              # Database connection & session management
│   └── session.py         # Async session factory
│
├── handlers/
│   ├── user/              # User commands (/start, /profile, payments, referrals)
│   ├── admin/             # Admin panel (admin_panel router)
│   └── generation/        # Generation flow (selection, process routers)
│
├── services/
│   ├── api_client.py      # Unified API facade for all generators
│   ├── generators/        # Generation logic by type
│   │   ├── standard_text.py
│   │   ├── standard_image.py
│   │   ├── seedream.py
│   │   ├── kling.py       # Video generation (FAL AI)
│   │   ├── veo.py         # Video generation (FAL AI)
│   │   └── wan.py         # Video generation (FAL AI)
│   └── providers/         # External API providers
│
├── middlewares/
│   ├── database.py        # DbSessionMiddleware (injects AsyncSession)
│   ├── auth.py            # Authentication middleware
│   └── throttling.py      # Rate limiting
│
├── keyboards/             # Inline keyboard builders
├── states/                # FSM state definitions
├── utils/                 # Utilities (logger setup)
└── logs/                  # Application logs (auto-created)
```

## Building and Running

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Environment variables in `.env` file

### Environment Variables (.env)
```bash
BOT_TOKEN=<telegram_bot_token>
ADMIN_IDS=<comma_separated_admin_ids>

DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/nexus
# or for local: DATABASE_URL=sqlite+aiosqlite:///nexus.db

OPENROUTER_API_KEY=<openrouter_api_key>
FAL_AI_API_KEY=<fal_ai_api_key>

BASE_URL=https://your-domain.com
WEB_PORT=8443

PLATEGA_MERCHANT_ID=<merchant_id>
PLATEGA_SECRET=<secret>
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the bot
python bot.py

# Run API tests
python test_api.py
```

### Docker Deployment
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Development Conventions

### Code Style
- **Imports**: Standard library → Third-party → Local (each group separated by blank line)
- **Type hints**: Required for all functions (use `Optional`, `List`, `Dict`, `Union`)
- **Naming**: 
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_prefix`

### Async Patterns
- All database operations must be async (`AsyncSession`)
- Use `async/await` for all I/O operations
- Context managers for sessions: `async with self.session_pool() as session:`

### Database (SQLAlchemy 2.0)
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
```

### Error Handling
- Log errors via `logger.exception()` or `logger.error()`
- Wrap external API calls in try-except
- Return `None` or error message on failure

### Aiogram Patterns
- Use `Router` pattern organized by functionality
- Inject session via middleware: `data["session"]`
- Use FSM for multi-step dialogs
- Callback data format: `category:action:payload`

### Service Layer
- Generators encapsulate provider-specific logic
- `APIClient` acts as facade for all generators
- Return types: `Optional[Union[str, BufferedInputFile]]`

### Testing
- Use `asyncio.run()` for async tests
- Tests require valid API keys in environment

## Key Constants

### Subscription Tiers (config.py)
```python
TARIFFS = {
    "day": {"price": 100, "gens": 10, "name": "🚀 Тест-драйв (10 шт)"},
    "week": {"price": 450, "gens": 50, "name": "📅 Неделька (50 шт)"},
    "month": {"price": 1600, "gens": 200, "name": "🗓 Месяц (200 шт)"},
    # ... more tiers
}

REF_LEVELS = [0.15, 0.10, 0.05]  # Referral reward percentages
```

### Model Categories (model_config.py)
- `gen_text`: 50+ text models (GPT, Claude, Gemini, etc.)
- `gen_image`: Flux, Stable Diffusion, Seedream, Gemini Image
- `gen_video`: Kling, Veo, Wan (via FAL AI)
- `gen_search`: Perplexity Sonar models

## Database Schema

### Core Tables
- **users**: User profiles, balances, subscriptions, referrals
- **generations**: Generation history (prompt, result, cost, status)
- **transactions**: Payment transactions (deposits, withdrawals, rewards)
- **message_history**: Conversation context per user/model
- **templates**: User-saved prompt templates
- **promocodes**: Promotional codes for token bonuses

## Middleware Chain
1. `DbSessionMiddleware` - Injects `AsyncSession` into handler data (must be first)
2. `AuthMiddleware` - User authentication checks
3. `ThrottlingMiddleware` - Rate limiting per user

## Important Notes
- Bot runs in **polling mode** by default (webhook support available)
- Russian language UI (texts in `config.py`)
- Debug handler logs all updates before routing
- Logs written to `logs/bot.log`

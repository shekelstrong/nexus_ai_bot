# AGENTS.md - Nexus AI Bot

## Обзор проекта
Python-бот для Telegram с генерацией текста/изображений/видео через OpenRouter и FAL AI APIs.

## Команды для сборки, проверки и тестов

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python bot.py

# Запуск конкретного теста (asyncio-based)
python test_api.py

# Миграции базы данных (Alembic)
alembic upgrade head

# Создание новой миграции
alembic revision --autogenerate -m "описание"
```

## Руководство по стилю кода

### Импорты
- Сначала импорты стандартной библиотеки
- Затем импорты сторонних библиотек
- Потом локальные импорты
- Каждая группа импортов разделена пустой строкой

```python
import asyncio
import logging

from aiogram import Bot, Dispatcher
from sqlalchemy import select

from config import settings
from handlers import user
```

### Аннотации типов
- Используйте `Optional[T]` для nullable типов
- Используйте `List`, `Dict`, `Union` из `typing`
- Обязательно указывайте тип возвращаемого значения для async функций

```python
from typing import Optional, List, Dict

async def generate_text(model: str, messages: List[Dict[str, str]]) -> Optional[str]:
    ...
```

### Соглашения об именовании
- **Классы**: PascalCase (`Database`, `DbSessionMiddleware`)
- **Функции/методы**: snake_case (`cmd_start`, `generate_text`)
- **Переменные**: snake_case
- **Константы**: UPPER_SNAKE_CASE (`BOT_TOKEN`, `REF_LEVELS`)
- **Приватные методы**: префикс подчёркивание (`_generate_fal_image_direct`)

### База данных (SQLAlchemy 2.0)
- Используйте DeclarativeBase с Mapped/mapped_column
- Определяйте связи через relationship()
- Включайте Index в __table_args__
- Используйте Enum из Python для строковых перечислений

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from enum import Enum as PyEnum

class Base(DeclarativeBase):
    pass

class SubscriptionTier(str, PyEnum):
    FREE = "FREE"
    PREMIUM = "PREMIUM"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
```

### Async/Await
- Все операции с БД должны быть асинхронными
- Используйте AsyncSession для доступа к базе данных
- Используйте контекстные менеджеры для сессий

```python
async def get_user(session: AsyncSession, telegram_id: int):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()
```

### Обработка ошибок
- Логируйте ошибки через logger.exception() или logger.error()
- Используйте try-except для внешних API вызовов
- Возвращайте None или сообщение об ошибке при сбое

```python
try:
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            if resp.status != 200:
                logger.error(f"API Error {resp.status}")
                return None
            result = await resp.json()
            return result
except Exception as e:
    logger.error(f"Exception: {e}")
    return None
```

### Хэндлеры Aiogram
- Используйте паттерн Router, организованный по функциональности
- Включайте session в словарь data через middleware
- Используйте FSM для состояния диалога

```python
from aiogram import Router, F
from aiogram.filters import CommandStart

router = Router(name="user_router")

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    ...
```

### Клавиатуры
- Используйте InlineKeyboardMarkup/InlineKeyboardButton
- Создавайте функции для динамических клавиатур
- Используйте формат callback_data: `category:action:payload`

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Изображения", callback_data="cat:gen_image")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])
```

### FSM состояния
- Определяйте StatesGroup для каждой функции
- Используйте понятные имена состояний
- Очищайте состояние после завершения

```python
from aiogram.fsm.state import State, StatesGroup

class GenState(StatesGroup):
    waiting_for_input = State()
    waiting_for_first_image = State()
```

### Конфигурация
- Используйте pydantic-settings BaseSettings
- Загружайте .env через python-dotenv
- Экспортируйте константы для обратной совместимости

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str = "sqlite+aiosqlite:///nexus.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

### Паттерн сервисов
- Создавайте классы генераторов для разных провайдеров
- APIClient как фасад для всех генераторов
- Модуль сервисов экспортирует __all__

```python
class StandardTextGenerator:
    def __init__(self):
        self.url = "https://api.example.com/v1"

    async def generate(self, model: str, prompt: str) -> Optional[str]:
        ...
```

### Middleware для Aiogram
- DbSessionMiddleware добавляет AsyncSession в data["session"]
- Регистрируйте через dp.update.middleware()
- Важно: DbSessionMiddleware должен быть первым middleware

```python
from middlewares.database import DbSessionMiddleware

dp.update.middleware(DbSessionMiddleware(session_pool=db.session_maker))
```

### BufferedInputFile для файлов
- Используйте для отправки сгенерированных изображений
- Возвращайте из сервисов как Union[str, BufferedInputFile]

```python
from aiogram.types import BufferedInputFile

async def generate_image(...) -> Optional[Union[str, BufferedInputFile]]:
    ...
```

### Логирование
- Используйте logger из utils.logger
- Логируйте на соответствующих уровнях (INFO, WARNING, ERROR)
- Включайте контекст в сообщения логов

```python
from utils.logger import logger

logger.info(f"Bot started: @{me.username}")
logger.error(f"Generation failed: {error}")
```

### Тестирование
- Используйте asyncio.run() для запуска async тестов
- Разделяйте тесты по моделям/эндпоинтам

```python
async def test_gemini():
    ...

async def main():
    await test_gemini()

if __name__ == "__main__":
    asyncio.run(main())
```

### Структура файлов
```
handlers/          - Хэндлеры команд и колбэков бота
services/          - Интеграции с внешними API
database/          - Модели, сессии, логика БД
middlewares/       - Middleware для Aiogram
keyboards/         - Билдеры инлайн-клавиатур
states/            - Определения FSM состояний
utils/             - Утилиты (логгер и др.)
logs/              - Логи бота (создаются автоматически)
```

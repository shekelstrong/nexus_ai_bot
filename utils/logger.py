import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

# Имя твоего логгера
APP_LOGGER_NAME = os.getenv("APP_LOGGER_NAME", "nexusai")

def _parse_level(level: Optional[str], default: int) -> int:
    if not level:
        return default
    try:
        return getattr(logging, level.upper(), default)
    except Exception:
        return default

class _ConfiguredOnce:
    done = False

def setup_logger(
    *,
    app_name: str = APP_LOGGER_NAME,
    app_level: Optional[str] = None,   # Уровень для твоего кода
    root_level: Optional[str] = None,  # Уровень для всего остального
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """
    Настраивает логирование:
    - app logger (твой код): пишет INFO и выше.
    - root logger (библиотеки): пишет WARNING и выше (чтобы убрать мусор).
    """

    if _ConfiguredOnce.done:
        return logging.getLogger(app_name)

    # Дефолтные уровни: Твой код - INFO, Чужой код - WARNING
    app_level_no = _parse_level(app_level or os.getenv("LOG_LEVEL"), logging.INFO)
    root_level_no = _parse_level(root_level or os.getenv("ROOT_LOG_LEVEL"), logging.WARNING)

    logs_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = log_file or os.getenv("LOG_FILE", os.path.join(logs_dir, "bot.log"))

    # Формат логов
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Настройка ROOT логгера (для библиотек) ---
    root = logging.getLogger()
    root.setLevel(root_level_no)

    # Очищаем старые хендлеры, если были
    if root.handlers:
        for h in root.handlers:
            root.removeHandler(h)

    # Консоль для root
    root_console = logging.StreamHandler()
    root_console.setLevel(root_level_no)
    root_console.setFormatter(console_fmt)

    # Файл для root
    root_file = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    root_file.setLevel(root_level_no)
    root_file.setFormatter(file_fmt)

    root.addHandler(root_console)
    root.addHandler(root_file)

    # --- Настройка APP логгера (твоего) ---
    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(app_level_no)
    app_logger.propagate = False  # Не дублировать в root

    if app_logger.handlers:
        for h in app_logger.handlers:
            app_logger.removeHandler(h)

    # Консоль для app
    app_console = logging.StreamHandler()
    app_console.setLevel(app_level_no)
    app_console.setFormatter(console_fmt)

    # Файл для app
    app_file = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    app_file.setLevel(app_level_no)
    app_file.setFormatter(file_fmt)

    app_logger.addHandler(app_console)
    app_logger.addHandler(app_file)

    # --- Глушим шумные библиотеки принудительно ---
    # Даже если в .env стоит DEBUG, эти ребята будут молчать
    noisy_modules = [
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "aiogram",
        "aiogram.event",
        "aiohttp",
        "asyncio",
        "httpcore",
        "httpx"
    ]
    
    for name in noisy_modules:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Вернуть Warnings в логи (например, DeprecationWarning)
    logging.captureWarnings(True)

    _ConfiguredOnce.done = True
    return app_logger

# Создаем логгер при импорте
logger = setup_logger()
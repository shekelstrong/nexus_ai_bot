# model_config.py

# Каталог моделей с группировкой по категориям и семействам
MODEL_CATALOG = {
    "gen_text": {
        "openai": {
            "models": [
                {"id": "openai/gpt-5", "name": "GPT-5", "cost": 15, "description": "Абсолютный флагман OpenAI. Непревзойденная логика, глубокий анализ данных и написание сложного кода."},
                {"id": "openai/gpt-5-mini", "name": "GPT-5 Mini", "cost": 5, "description": "Идеальный баланс между скоростью, ценой и интеллектом."},
                {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "cost": 1, "description": "Молниеносная и дешевая модель для повседневных задач."},
            ]
        },
        "anthropic": {
            "models": [
                {"id": "anthropic/claude-opus-4.5", "name": "Claude Opus 4.5", "cost": 20, "description": "Самая мощная модель Anthropic. Анализ, написание текстов, дизайн контента на высшем уровне."},
                {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "cost": 8, "description": "Золотой стандарт для работы с текстами и контентом. Пишет естественно, по-человечески."},
                {"id": "anthropic/claude-haiku-4.5", "name": "Claude Haiku 4.5", "cost": 2, "description": "Быстрая и дешевая модель для коротких запросов."},
            ]
        },
        "google": {
            "models": [
                {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "cost": 5, "description": "Флагман от Google с гигантским контекстным окном. Идеальна для анализа больших текстов."},
                {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "cost": 2, "description": "Быстрая и эффективная модель Google для ежедневных задач."},
                {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "cost": 1, "description": "Надежная базовая модель Google."},
            ]
        },
        "deepseek": {
            "models": [
                {"id": "deepseek/deepseek-v3.2", "name": "DeepSeek V3.2", "cost": 3, "description": "Пишет код на уровне лучших моделей мира, но стоит в разы дешевле."},
                {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "cost": 2, "description": "Рассуждающая модель. Логически решает сложные задачи по шагам."},
            ]
        },
        "xai": {
            "models": [
                {"id": "x-ai/grok-4.1-fast", "name": "Grok 4.1 Fast", "cost": 5, "description": "ИИ от Илона Маска. Доступ к свежим данным и минимум ограничений."},
                {"id": "x-ai/grok-4-fast", "name": "Grok 4 Fast", "cost": 4, "description": "Предыдущая, но всё еще мощная версия Grok."},
                {"id": "x-ai/grok-code-fast-1", "name": "Grok Code Fast 1", "cost": 3, "description": "Специальная версия Grok, заточенная исключительно под написание и ревью кода."},
            ]
        },
        "qwen": {
            "models": [
                {"id": "qwen/qwen3-coder", "name": "Qwen3 Coder", "cost": 2, "description": "Специализированная нейросеть-программист от Alibaba. Топовый кодинг за копейки."},
                {"id": "qwen/qwen3-235b-a22b-2507", "name": "Qwen3 235B A22B", "cost": 3, "description": "Гигантская модель на 235 миллиардов параметров с огромной базой знаний."},
            ]
        },
        "moonshotai": {
            "models": [
                {"id": "moonshotai/kimi-k2-0905", "name": "Kimi K2 0905", "cost": 3, "description": "Китайская модель Kimi, славящаяся способностью читать гигантские тексты без потери смысла."},
            ]
        },
        "mistral": {
            "models": [
                {"id": "mistralai/mistral-nemo", "name": "Mistral Nemo", "cost": 2, "description": "Эффективная европейская модель. Отличная логика и знание множества языков."},
            ]
        },
    },

    "gen_image": {
        "image_models": {
            "models": [
                {"id": "yandex/yandex-art", "name": "Яндекс Арт", "cost": 3, "description": "Яндекс Арт — генерация изображений от Yandex. Аспекты: 1:1, 9:16, 16:9."},
                {"id": "openai/gpt-5.4-image-2", "name": "GPT Images 2", "cost": 8, "description": "GPT-5.4 + GPT Image 2 от OpenAI. Многомодальная генерация с высшим качеством."},
                {"id": "qwen/image-2", "name": "Qwen Image 2", "cost": 3, "description": "Qwen Image 2 — генерация изображений от Alibaba. Аспекты: 1:1, 9:16, 16:9."},
                {"id": "bytedance/seedream-5-lite", "name": "Seedream 5.0", "cost": 3, "description": "Seedream 5.0 Lite от ByteDance. Яркие, сочные цвета и отличная стилизация."},
                {"id": "google/gemini-3.1-flash-image-preview", "name": "Nano Banana 2", "cost": 10, "description": "Наша топовая эксклюзивная модель! Создает и редактирует изображения с невероятной магией."},
                {"id": "topaz/image-upscale", "name": "Топаз Апскейлер", "cost": 5, "description": "Топаз Апскейлер — улучшение и увеличение изображений. Аспекты: 1:1, 9:16, 16:9."},
                {"id": "x-ai/grok-imagine-image", "name": "Грок Image", "cost": 4, "description": "Грок Image — генерация изображений от xAI (Илон Маск). Аспекты: 1:1, 9:16, 16:9."},
                {"id": "black-forest-labs/flux.2-pro", "name": "FLUX 2 PRO", "cost": 4, "description": "FLUX 2 PRO — лучшая модель для фотореализма. Идеально рисует лица и пальцы."},
                {"id": "black-forest-labs/flux.2-flex", "name": "FLUX-2 FLEX", "cost": 2, "description": "FLUX-2 FLEX — сбалансированная версия Flux. Рисует быстро и качественно."},
            ]
        },
    },

    "gen_nano_banana": {
        "nano_banana": {
            "models": [
                {"id": "google/gemini-3-pro-image-preview", "name": "Nano Banana Pro", "cost": 8, "description": "Профессиональная генерация артов и фотореализма высшего качества."},
                {"id": "google/gemini-2.5-flash-image", "name": "Nano Banana", "cost": 3, "description": "Быстрая, креативная и недорогая генерация изображений для повседневных задач."},
            ]
        },
    },

    "gen_video": {
        "video_models": {
            "models": [
                {"id": "bytedance/seedance-2-fast", "name": "Seedance 2 Fast", "cost": 70, "description": "Seedance 2 Fast — быстрая видео генерация от ByteDance. 720p/1080p, 5/10/15 сек.", "default_duration": "5"},
                {"id": "bytedance/seedance-2", "name": "Seedance 2", "cost": 100, "description": "Seedance 2 — премиум генерация видео от ByteDance. 720p/1080p, 5/10/15 сек.", "default_duration": "10"},
                {"id": "kling/v3-motion-control", "name": "Kling 3 Motion Control", "cost": 35, "description": "Kling 3 Motion Control — перенос движений с референса. 720p/1080p, 5/10/15 сек."},
                {"id": "topaz/video-upscale", "name": "Топаз Видео Апскейлер", "cost": 50, "description": "Топаз Видео Апскейлер — улучшение и увеличение видео. 720p/1080p, 5/10/15 сек."},
                {"id": "wan/2.6", "name": "WAN-2,6", "cost": 20, "description": "WAN-2.6 — видео генерация из текста. 720p/1080p, 5/10/15 сек."},
                {"id": "google/veo3_fast", "name": "VEO 3.1 Fast", "cost": 30, "description": "VEO 3.1 Fast — быстрая видео генерация от Google. 720p/1080p, 5/10/15 сек."},
                {"id": "google/veo3", "name": "VEO 3.1 Pro", "cost": 35, "description": "VEO 3.1 Pro — премиум видео генерация от Google. 720p/1080p, 5/10/15 сек."},
            ]
        },
    },

    "gen_search": {
        "perplexity": {
            "models": [
                {"id": "perplexity/sonar-pro-search", "name": "Sonar Pro Search", "cost": 5, "description": "Умнейший ИИ-поисковик. Сам гуглит информацию в реальном времени и выдает точный ответ со ссылками."},
                {"id": "perplexity/sonar-pro", "name": "Sonar Pro", "cost": 4, "description": "Продвинутая поисковая модель Perplexity. Отличный аналитик свежих новостей."},
                {"id": "perplexity/sonar-deep-research", "name": "Sonar Deep Research", "cost": 6, "description": "Глубокое исследование темы. Модель изучает десятки сайтов, чтобы написать подробный доклад."},
                {"id": "perplexity/sonar-reasoning-pro", "name": "Sonar Reasoning Pro", "cost": 5, "description": "Ищет информацию в интернете и применяет цепочки рассуждений для сложных выводов."},
                {"id": "perplexity/sonar-reasoning", "name": "Sonar Reasoning", "cost": 2, "description": "Базовая модель рассуждений на основе свежих данных из сети."},
                {"id": "perplexity/sonar", "name": "Sonar", "cost": 1, "description": "Простой и быстрый поиск по интернету без лишней воды."},
                {"id": "perplexity/r1-1776", "name": "R1 1776", "cost": 3, "description": "Альтернативная модель Perplexity для специфичных поисковых запросов."},
                {"id": "perplexity/llama-3.1-sonar-large-128k-online", "name": "Llama 3.1 Sonar Large", "cost": 2, "description": "Мощная открытая модель Llama, подключенная к интернету. Огромная память (128k)."},
                {"id": "perplexity/llama-3.1-sonar-small-128k-online", "name": "Llama 3.1 Sonar Small", "cost": 1, "description": "Легкая интернет-версия Llama для быстрых справок."},
                {"id": "perplexity/llama-3-sonar-large-32k-chat", "name": "Llama 3 Sonar Large Chat", "cost": 2, "description": "Чат-версия Llama 3 с интеграцией актуальных данных Perplexity."},
                {"id": "perplexity/llama-3-sonar-small-32k-online", "name": "Llama 3 Sonar Small Online", "cost": 1, "description": "Облегченный поиск на базе Llama 3."},
                {"id": "perplexity/llama-3-sonar-small-32k-chat", "name": "Llama 3 Sonar Small Chat", "cost": 1, "description": "Базовая модель для чата со встроенным веб-поиском."},
                {"id": "perplexity/llama-3-sonar-large-32k-online", "name": "Llama 3 Sonar Large Online", "cost": 2, "description": "Крупная модель поиска для получения развернутых ответов из сети."},
            ]
        }
    }
}

# Получить все модели одним словарем
ALL_MODEL_IDS = {}
for category, families in MODEL_CATALOG.items():
    for family_key, family_data in families.items():
        for model in family_data["models"]:
            ALL_MODEL_IDS[model["id"]] = model

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
        "flux": {
            "models": [
                {"id": "black-forest-labs/flux.2-pro", "name": "Flux 2.0 Pro", "cost": 4, "description": "Лучшая модель для фотореализма. Идеально рисует лица, пальцы и понимает текст на картинках."},
                {"id": "black-forest-labs/flux.2-max", "name": "Flux 2.0 Max", "cost": 4, "description": "Максимальная детализация. Для сложных артов с обилием мелких объектов."},
                {"id": "black-forest-labs/flux.2-flex", "name": "Flux 2.0 Flex", "cost": 2, "description": "Сбалансированная версия Flux. Рисует быстро и качественно."},
                {"id": "black-forest-labs/flux.2-klein-4b", "name": "Flux 2.0 Klein", "cost": 1, "description": "Самая быстрая и легкая версия Flux для черновиков и набросков."},
                {"id": "fal-ai/stable-diffusion-v35-large", "name": "Stable Diffusion v3.5 Large", "cost": 3, "description": "Легендарная классика в обновленном виде. Широкие возможности стилизации."},
            ]
        },
        "riverflow": {
            "models": [
                {"id": "sourceful/riverflow-v2-max-preview", "name": "Riverflow v2 Max", "cost": 4, "description": "Мощная генерация изображений с высокой эстетической привлекательностью."},
                {"id": "sourceful/riverflow-v2-standard-preview", "name": "Riverflow v2 Standard", "cost": 2, "description": "Стандартная версия Riverflow для качественного арта."},
                {"id": "sourceful/riverflow-v2-fast-preview", "name": "Riverflow v2 Fast", "cost": 1, "description": "Облегченная версия Riverflow для быстрой отрисовки идей."},
            ]
        },
        "seedream": {
            "models": [
                {"id": "bytedance-seed/seedream-4.5", "name": "Seedream 4.5", "cost": 3, "description": "Нейросеть от создателей TikTok. Яркие, сочные цвета и отличная стилизация."},
            ]
        },
        "gemini_image": {
            "models": [
                {"id": "openai/gpt-5-image", "name": "GPT-5 Image", "cost": 5, "description": "Флагманский генератор изображений от создателей ChatGPT. Идеальное понимание сложных промптов."},
                {"id": "openai/gpt-5-image-mini", "name": "GPT-5 Image Mini", "cost": 2, "description": "Облегченная версия генератора для быстрого создания креативов."},
                {"id": "openai/gpt-image-2", "name": "GPT Image 2", "cost": 4, "description": "Новая генерация изображений от OpenAI. Высокая детализация и точное следование инструкциям."},
            ]
        },
    },

    "gen_nano_banana": {
        "nano_banana": {
            "models": [
                {"id": "google/gemini-3.1-flash-image-preview", "name": "Nano Banana 2", "cost": 10, "description": "Наша топовая эксклюзивная модель! Создает и редактирует изображения с невероятной магией."},
                {"id": "google/gemini-3-pro-image-preview", "name": "Nano Banana Pro", "cost": 8, "description": "Профессиональная генерация артов и фотореализма высшего качества."},
                {"id": "google/gemini-2.5-flash-image", "name": "Nano Banana", "cost": 3, "description": "Быстрая, креативная и недорогая генерация изображений для повседневных задач."},
            ]
        },
    },

    "gen_video": {
        # Подраздел “Видео по фото” (img2vid)
        "video_from_photo": {
            "models": [
                {"id": "fal-ai/kling-video/v2.6/pro/image-to-video", "name": "Kling 2.6", "cost": 35, "description": "Оживляет любую вашу фотографию. Отправьте 1 фото."},
                {"id": "fal-ai/veo3.1/image-to-video", "name": "Veo 3.1 (по 1 фото)", "cost": 30, "description": "Оживляет статичные картинки с естественной физикой Google. Отправьте 1 фото."},
                {"id": "fal-ai/veo3.1/first-last-frame-to-video", "name": "Veo 3.1 (по 2 фото)", "cost": 30, "description": "Магия переходов: отправьте начальный и конечный кадр, нейросеть додумает видео между ними."},
                {"id": "fal-ai/seedance-1-0/image-to-video", "name": "Seedance 2.0", "cost": 100, "description": "Премиум генерация видео из фото. Высочайшее качество анимации."},
            ]
        },
        # Подраздел “Видео по образцу” (motion-control)
        "video_from_motion": {
            "models": [
                {"id": "fal-ai/kling-video/v2.6/pro/motion-control", "name": "Kling Motion", "cost": 35, "description": "Переносит движения с видео-референса на персонажа с фото."},
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
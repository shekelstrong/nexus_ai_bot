# model_config.py

# Каталог моделей с группировкой по категориям и семействам
MODEL_CATALOG = {
    "gen_text": {
        "openai": {
            "models": [
                {"id": "openai/gpt-5", "name": "GPT-5", "cost": 15, "description": "Абсолютный флагман OpenAI. Непревзойденная логика, глубокий анализ данных и написание сложного кода."},
                {"id": "openai/gpt-5.2", "name": "GPT-5.2", "cost": 20, "description": "Экспериментальная сверхмощная версия GPT-5. Максимальная креативность и понимание сложнейших контекстов."},
                {"id": "openai/gpt-5-mini", "name": "GPT-5 Mini", "cost": 5, "description": "Облегченная версия GPT-5. Идеальный баланс между скоростью, ценой и выдающимся интеллектом."},
                {"id": "openai/gpt-5-nano", "name": "GPT-5 Nano", "cost": 1, "description": "Самая быстрая и дешевая модель 5-го поколения для простых повседневных задач."},
                {"id": "openai/gpt-4.1", "name": "GPT-4.1", "cost": 10, "description": "Улучшенная версия классического GPT-4. Отличный выбор для копирайтинга и переводов."},
                {"id": "openai/gpt-4.1-mini", "name": "GPT-4.1 Mini", "cost": 4, "description": "Быстрая версия GPT-4.1. Отлично справляется с рутиной и ответами на простые вопросы."},
                {"id": "openai/gpt-4o", "name": "GPT-4o", "cost": 5, "description": "Универсальная и очень быстрая модель (Omni). Прекрасно рассуждает и поддерживает живой диалог."},
                {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "cost": 1, "description": "Младший брат GPT-4o. Работает молниеносно, потребляет минимум токенов."},
                {"id": "openai/o3-mini", "name": "OpenAI o3-mini", "cost": 3, "description": "Специализированная модель для точных математических расчетов и STEM-задач."},
                {"id": "openai/o1", "name": "OpenAI o1", "cost": 8, "description": "Модель с глубоким логическим мышлением. Берет паузу на 'подумать', прежде чем выдать идеальный ответ."},
                {"id": "openai/gpt-oss-120b", "name": "GPT- OSS 120B", "cost": 2, "description": "Мощная open-source модель на базе архитектуры GPT с огромным объемом знаний."},
                {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B", "cost": 1, "description": "Быстрая 20-миллиардная open-source модель для базовых генераций текста."},
            ]
        },
        "anthropic": {
            "models": [
                {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "cost": 8, "description": "Легенда кодинга и работы с текстами. Пишет максимально естественно, по-человечески."},
                {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "cost": 6, "description": "Предыдущее поколение Sonnet. Надежная классика для работы с документами."},
                {"id": "anthropic/claude-opus-4.5", "name": "Claude Opus 4.5", "cost": 20, "description": "Самая тяжелая и умная модель Anthropic. Для самых сложных аналитических задач."},
                {"id": "anthropic/claude-haiku-4.5", "name": "Claude Haiku 4.5", "cost": 2, "description": "Невероятно быстрая модель. Читает и анализирует тексты со скоростью света."},
                {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "cost": 5, "description": "Золотой стандарт среди разработчиков. Одна из лучших моделей для программирования."},
                {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "cost": 15, "description": "Классический 'тяжеловес' от Anthropic 3-го поколения."},
                {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "cost": 1, "description": "Простая, быстрая и дешевая модель для коротких запросов."},
            ]
        },
        "google": {
            "models": [
                {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "cost": 5, "description": "Флагман от Google с гигантским контекстным окном. Идеальна для анализа целых книг и кода."},
                {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "cost": 2, "description": "Быстрая и эффективная модель от Google для ежедневных задач."},
                {"id": "google/gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "cost": 1, "description": "Максимально облегченная версия Gemini для мгновенных ответов."},
                {"id": "google/gemini-2.5-flash-lite-preview-09-2025", "name": "Gemini 2.5 Flash Lite Preview", "cost": 1, "description": "Тестовая версия легкой модели с экспериментальными функциями."},
                {"id": "google/gemini-3-pro-preview", "name": "Gemini 3 Pro Preview", "cost": 8, "description": "Предрелизная версия 3-го поколения. Будущее ИИ от Google в ваших руках."},
                {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash Preview", "cost": 3, "description": "Быстрая версия 3-го поколения. Тестируйте новые алгоритмы Google первыми."},
                {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "cost": 1, "description": "Надежная базовая модель Google 2-го поколения."},
            ]
        },
        "deepseek": {
            "models": [
                {"id": "deepseek/deepseek-v3.2", "name": "DeepSeek V3.2", "cost": 3, "description": "Хит сезона! Пишет код на уровне лучших моделей мира, но стоит в разы дешевле."},
                {"id": "deepseek/deepseek-chat-v3.1", "name": "DeepSeek Chat V3.1", "cost": 2, "description": "Отличная разговорная модель от китайских разработчиков."},
                {"id": "deepseek/deepseek-chat-v3-0324", "name": "DeepSeek Chat V3 0324", "cost": 2, "description": "Стабильный билд разговорной модели DeepSeek."},
                {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "cost": 2, "description": "Специальная 'рассуждающая' модель (Reasoning). Логически решает сложные задачи по шагам."},
            ]
        },
        "meta": {
            "models": [
                {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "cost": 1, "description": "Популярная открытая модель от Meta. Быстрая, легкая и без жесткой цензуры."},
            ]
        },
        "xai": {
            "models": [
                {"id": "x-ai/grok-4.1-fast", "name": "Grok 4.1 Fast", "cost": 5, "description": "ИИ от Илона Маска. Дерзкий характер, доступ к свежим данным и минимум ограничений."},
                {"id": "x-ai/grok-4-fast", "name": "Grok 4 Fast", "cost": 4, "description": "Предыдущая, но всё еще мощная версия бунтаря Grok."},
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
        "tngtech": {
            "models": [
                {"id": "tngtech/deepseek-r1t2-chimera:free", "name": "DeepSeek R1T2 Chimera (Free)", "cost": 0, "description": "Бесплатная экспериментальная рассуждающая модель на базе DeepSeek."},
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
        "kling": {
            "models": [
                {"id": "fal-ai/kling-video/v2.6/pro/text-to-video", "name": "Kling 2.6 Pro (Text)", "cost": 35, "description": "Генерирует кинематографичные видео по текстовому описанию. Лучшая физика движений."},
                {"id": "fal-ai/kling-video/v2.6/pro/image-to-video", "name": "Kling 2.6 Pro (Img2Vid)", "cost": 35, "description": "Оживляет любую вашу фотографию, превращая её в потрясающий видеоролик."},
                {"id": "fal-ai/kling-video/v2.6/pro/motion-control", "name": "Kling 2.6 Pro (Motion)", "cost": 35, "description": "Переносит движения с видео-референса на вашего персонажа с фото (Motion Transfer)."},
                {"id": "fal-ai/kling-video/v2.6/standard/motion-control", "name": "Kling 2.6 Std (Motion)", "cost": 20, "description": "Бюджетная версия захвата движений для анимации персонажей."},
            ]
        },
        "veo": {
            "models": [
                {"id": "fal-ai/veo3.1", "name": "Veo 3.1 (Text)", "cost": 30, "description": "Прорывная видеомодель от Google. Создает сверхреалистичные ролики по тексту."},
                {"id": "fal-ai/veo3.1/image-to-video", "name": "Veo 3.1 (Img2Vid)", "cost": 30, "description": "Оживляет статичные картинки с невероятным качеством и естественной физикой Google."},
                {"id": "fal-ai/veo3.1/extend-video", "name": "Veo 3.1 (Extend)", "cost": 30, "description": "Берет ваше существующее видео и плавно дорисовывает его продолжение."},
                {"id": "fal-ai/veo3.1/reference-to-video", "name": "Veo 3.1 (Ref2Vid)", "cost": 30, "description": "Генерирует видео в стилистике предоставленного референса."},
                {"id": "fal-ai/veo3.1/first-last-frame-to-video", "name": "Veo 3.1 (First-Last)", "cost": 30, "description": "Магия переходов: отправьте начальный и конечный кадр, а нейросеть додумает видео между ними."},
                {"id": "fal-ai/veo3.1/fast", "name": "Veo 3.1 Fast (Text)", "cost": 15, "description": "Ускоренная генерация видео по тексту от Google."},
                {"id": "fal-ai/veo3.1/fast/image-to-video", "name": "Veo 3.1 Fast (Img2Vid)", "cost": 15, "description": "Ускоренное 'оживление' фотографий."},
                {"id": "fal-ai/veo3.1/fast/extend-video", "name": "Veo 3.1 Fast (Extend)", "cost": 15, "description": "Ускоренное продолжение вашего видеоролика."},
                {"id": "fal-ai/veo3.1/fast/first-last-frame-to-video", "name": "Veo 3.1 Fast (First-Last)", "cost": 15, "description": "Ускоренная анимация перехода между двумя фотографиями."},
            ]
        },
        "wan": {
            "models": [
                {"id": "wan/v2.6/text-to-video", "name": "Wan 2.6 (Text)", "cost": 25, "description": "Свежая модель для генерации стильных видеороликов по тексту."},
                {"id": "wan/v2.6/image-to-video", "name": "Wan 2.6 (Img2Vid)", "cost": 25, "description": "Анимация картинок с акцентом на плавность и кинематографичность."},
                {"id": "wan/v2.6/reference-to-video", "name": "Wan 2.6 (Ref2Vid)", "cost": 25, "description": "Создание видеороликов на основе визуального стиля вашего референса."},
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
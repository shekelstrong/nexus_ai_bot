from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from model_config import MODEL_CATALOG
from config import SUBSCRIPTION_TIERS, TOKEN_PACKAGES

def main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍌 Nano Banana", callback_data="cat:gen_nano_banana", style="success"),
        ],
        [
            InlineKeyboardButton(text="🤖 Текст", callback_data="cat:gen_text", style="primary"),
            InlineKeyboardButton(text="🎨 Изображения", callback_data="cat:gen_image", style="primary")
        ],
        [
            InlineKeyboardButton(text="🎥 Видео", callback_data="cat:gen_video", style="primary"),
            InlineKeyboardButton(text="✏️ Промпт", callback_data="cat:gen_prompt", style="primary")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="💎 Токены", callback_data="subscriptions", style="success")
        ],
        [
            InlineKeyboardButton(text="📊 История", callback_data="history"),
            InlineKeyboardButton(text="🎁 Рефералка", callback_data="referrals", style="success")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Поддержка", callback_data="support", style="danger")
        ]
    ])
    return kb

def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu", style="success")]
    ])


def video_category_menu() -> InlineKeyboardMarkup:
    """Меню подразделов видео."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Видео по фото", callback_data="family:gen_video:video_from_photo", style="primary")],
        [InlineKeyboardButton(text="🎥 Видео по образцу", callback_data="family:gen_video:video_from_motion", style="primary")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")]
    ])


def text_models_menu() -> InlineKeyboardMarkup:
    """Меню выбора текстовых моделей (бренды без семейств)."""
    from model_config import MODEL_CATALOG
    families = MODEL_CATALOG.get("gen_text", {})
    brand_icons = {
        "openai": "🧠 ChatGPT (OpenAI)",
        "anthropic": "🟣 Claude (Anthropic)",
        "google": "🔵 Gemini (Google)",
        "deepseek": "🔥 DeepSeek",
        "xai": "⚡️ Grok (xAI)",
    }
    buttons = []
    for fam_key in families:
        title = brand_icons.get(fam_key, fam_key.capitalize())
        buttons.append([InlineKeyboardButton(
            text=title,
            callback_data=f"family:gen_text:{fam_key}",
            style="primary"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def prompt_menu() -> InlineKeyboardMarkup:
    """Меню раздела Промпт."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼️ Промпт для фото", callback_data="prompt_for_image", style="primary")],
        [InlineKeyboardButton(text="🎥 Промпт для видео", callback_data="prompt_for_video", style="primary")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")]
    ])


def video_prompt_duration_menu() -> InlineKeyboardMarkup:
    """Выбор длительности промпта для видео."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 секунд", callback_data="vprompt_dur:5", style="primary"),
            InlineKeyboardButton(text="10 секунд", callback_data="vprompt_dur:10", style="primary")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="cat:gen_prompt", style="success")]
    ])


def image_size_menu() -> InlineKeyboardMarkup:
    """Выбор размера изображения для GPT Image моделей."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1:1 (квадрат)", callback_data="isize:1:1", style="primary"),
            InlineKeyboardButton(text="2:3 (портрет)", callback_data="isize:2:3", style="primary"),
        ],
        [
            InlineKeyboardButton(text="3:2 (альбом)", callback_data="isize:3:2", style="primary"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")]
    ])


def video_format_menu() -> InlineKeyboardMarkup:
    """Выбор формата видео."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="9:16 (вертикальное)", callback_data="vformat:9:16", style="primary"),
            InlineKeyboardButton(text="16:9 (горизонтальное)", callback_data="vformat:16:9", style="primary")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")]
    ])


def video_duration_menu() -> InlineKeyboardMarkup:
    """Выбор длительности видео."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 секунд", callback_data="vduration:5", style="primary"),
            InlineKeyboardButton(text="10 секунд", callback_data="vduration:10", style="primary")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")]
    ])


def post_video_gen_kb(model_id: str, gen_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура после видеогенерации: Снова + Меню."""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Снова в этой модели", callback_data=f"regen_model:{model_id}", style="primary"),
        ],
        [
            InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu", style="success")
        ]
    ]
    if gen_id:
        buttons.insert(0, [
            InlineKeyboardButton(text="📢 Поделиться", callback_data=f"share_gen:{gen_id}", style="primary")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def post_generation_kb(gen_id: int = None, model_id: str = None) -> InlineKeyboardMarkup:
    """Клавиатура после генерации."""
    buttons = []

    if model_id:
        buttons.append([
            InlineKeyboardButton(text="🔄 Снова в этой модели", callback_data=f"regen_model:{model_id}", style="primary")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🔄 Заново", callback_data="restart_gen", style="primary")
        ])

    buttons.append([
        InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu", style="success")
    ])

    if gen_id:
        buttons.insert(0, [
            InlineKeyboardButton(text="📢 Поделиться в канал", callback_data=f"share_gen:{gen_id}", style="primary")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def try_prompt_kb(gen_id: int) -> InlineKeyboardMarkup:
    """Кнопка для канала 'Попробовать этот промпт' (Deep Link)"""
    url = f"https://t.me/nexsai_bot?start=gen_{gen_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Попробовать этот промпт", url=url)]
    ])

def confirm_try_prompt_kb(gen_id: int) -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет(Изменить) для запуска чужого промпта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Запустить генерацию", callback_data=f"run_gen:{gen_id}", style="success")],
        [InlineKeyboardButton(text="✏️ Изменить настройки", callback_data=f"edit_gen:{gen_id}", style="primary")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu", style="danger")]
    ])

def cancel_generation_menu() -> InlineKeyboardMarkup:
    """Клавиатура для отмены текущего процесса генерации."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_menu", style="danger")]
    ])

def model_families_menu(category: str) -> InlineKeyboardMarkup:
    """Меню выбора семейства моделей в определенной категории (компактно по 2)."""
    families = MODEL_CATALOG.get(category, {})
    
    family_titles = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "google": "Google",
        "mistral": "Mistral",
        "meta": "Meta (Llama)",
        "xai": "xAI (Grok)",
        "deepseek": "DeepSeek",
        "qwen": "Qwen",
        "nvidia": "NVIDIA",
        "other": "Другие",
        "free": "Бесплатные",
        "seedream": "Seedream",
        "gemini_image": "GPT Images",
        "fal_ai_image": "Flux & SD",
        "other_image": "Другие",
        "kling": "Kling AI",
        "veo": "Google Veo",
        "wan": "Wan Video",
        "fal_ai_video": "Polza Video",
        "perplexity": "Perplexity",
        "google_search": "Google Search"
    }
    
    buttons = []
    row = []
    
    for fam_key, fam_data in families.items():
        title = family_titles.get(fam_key, fam_key.capitalize())
        models_count = len(fam_data.get("models", []))
        if models_count > 0:
            row.append(InlineKeyboardButton(
                text=f"{title} ({models_count})",
                callback_data=f"family:{category}:{fam_key}",
                style="primary"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
                
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def models_list_menu(category: str, family: str) -> InlineKeyboardMarkup:
    """Меню выбора конкретной модели (компактно по 2)."""
    models = MODEL_CATALOG.get(category, {}).get(family, {}).get("models", [])
    buttons = []
    row = []
    
    for model in models:
        cost_text = f"💎 {model.get('cost', 0)}" if model.get('cost', 0) > 0 else "Беспл."
        row.append(InlineKeyboardButton(
            text=f"{model['name']} [{cost_text}]",
            callback_data=f"set_model:{model['id']}",
            style="primary"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)
            
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{category}", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def nano_banana_menu() -> InlineKeyboardMarkup:
    """Меню выбора моделей Nano Banana."""
    models = MODEL_CATALOG.get("gen_nano_banana", {}).get("nano_banana", {}).get("models", [])
    buttons = []
    
    for model in models:
        if "free" in model['id'].lower():
            text = f"🍌 {model['name']}"
        else:
            cost_text = f"💎 {model.get('cost', 0)}"
            text = f"🍌 {model['name']} [{cost_text}]"
            
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"set_model:{model['id']}",
            style="primary"
        )])
        
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_menu() -> InlineKeyboardMarkup:
    """Меню профиля."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Пополнить баланс", callback_data="subscriptions", style="success")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")]
    ])

def subscription_tiers_menu() -> InlineKeyboardMarkup:
    """Меню тарифов подписки и пакетов."""
    keyboard = []
    for tier_id, tier_data in SUBSCRIPTION_TIERS.items():
        if tier_id == "FREE":
            continue
        keyboard.append([InlineKeyboardButton(
            text=f"{tier_data['name']} - {tier_data['price']}₽",
            callback_data=f"tier_{tier_id}",
            style="success"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🪙 Пакеты токенов", callback_data="packet_tokens", style="primary")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def token_package_menu() -> InlineKeyboardMarkup:
    """Меню покупки пакетов токенов."""
    keyboard = []
    for packet_id, packet_data in TOKEN_PACKAGES.items():
        keyboard.append([InlineKeyboardButton(
            text=f"{packet_data['name']} - {packet_data['price']}₽",
            callback_data=f"buy_packet:{packet_id}",
            style="success"
        )])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="subscriptions", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
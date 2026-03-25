from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from model_config import MODEL_CATALOG
from config import SUBSCRIPTION_TIERS, TOKEN_PACKAGES

def main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота (ОРИГИНАЛЬНОЕ)."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍌 Nano Banana", callback_data="cat:gen_nano_banana", style="primary"),
            InlineKeyboardButton(text="🤖 Текст", callback_data="cat:gen_text", style="primary")
        ],
        [
            InlineKeyboardButton(text="🌐 Perplexity", callback_data="cat:gen_search", style="primary"),
            InlineKeyboardButton(text="🎨 Изображения", callback_data="cat:gen_image", style="primary")
        ],
        [
            InlineKeyboardButton(text="🎬 Видео", callback_data="cat:gen_video", style="primary")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="💎 Подписка", callback_data="subscriptions", style="success")
        ],
        [
            InlineKeyboardButton(text="📊 История", callback_data="history"),
            InlineKeyboardButton(text="🎁 Рефералка", callback_data="referrals", style="success")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Поддержка", callback_data="support")
        ]
    ])
    return kb

def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu")]
    ])

def post_generation_kb() -> InlineKeyboardMarkup:
    """Клавиатура после генерации с кнопкой Заново."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Заново", callback_data="restart_gen", style="primary"), 
            InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu")
        ]
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
        "fal_ai_image": "Midjourney & Flux",
        "other_image": "Другие",
        "kling": "Kling AI",
        "veo": "Google Veo",
        "wan": "Wan Video",
        "fal_ai_video": "FAL AI Video",
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
        
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
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
            
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{category}")])
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
        
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_menu() -> InlineKeyboardMarkup:
    """Меню профиля."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Пополнить баланс", callback_data="subscriptions", style="success")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
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
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
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
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="subscriptions")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
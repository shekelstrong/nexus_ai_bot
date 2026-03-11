from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from model_config import MODEL_CATALOG
from config import SUBSCRIPTION_TIERS, TOKEN_PACKAGES

def main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Подписка", callback_data="open_subscription")],
        [InlineKeyboardButton(text="🍌 Nano Banana", callback_data="cat:gen_nano_banana")],
        [InlineKeyboardButton(text="🤖 Текстовые нейросети", callback_data="cat:gen_text")],
        [InlineKeyboardButton(text="🎨 Изображения", callback_data="cat:gen_image")],
        [InlineKeyboardButton(text="🎬 Видео-генерация", callback_data="cat:gen_video")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="🌐 Поиск в интернете", callback_data="cat:gen_search")],
        [InlineKeyboardButton(text="👨‍💻 Поддержка / FAQ", url="https://t.me/nedopekin")],
    ])
    return keyboard

def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu")]
    ])

def post_generation_kb() -> InlineKeyboardMarkup:
    """Клавиатура после генерации с кнопкой Заново."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Заново", callback_data="restart_gen"), InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu")]
    ])

def model_families_menu(category: str) -> InlineKeyboardMarkup:
    """Меню выбора семейства моделей в определенной категории."""
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
        "other": "Другие текстовые",
        "free": "Бесплатные",
        "seedream": "Seedream",
        "gemini_image": "GPT Images",
        "fal_ai_image": "FAL AI (Midjourney & Flux)",
        "other_image": "Другие графические",
        "kling": "Kling AI",
        "veo": "Veo",
        "wan": "Wan",
        "fal_ai_video": "FAL AI Video",
        "perplexity": "Perplexity",
        "google_search": "Google Search"
    }
    
    keyboard = []
    
    for family_key, family_data in families.items():
        title = family_titles.get(family_key, family_key.capitalize())
        models_count = len(family_data.get("models", []))
        if models_count > 0:
            keyboard.append([InlineKeyboardButton(
                text=f"{title} ({models_count})",
                callback_data=f"family:{category}:{family_key}"
            )])
            
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def models_list_menu(category: str, family: str) -> InlineKeyboardMarkup:
    """Меню выбора конкретной модели."""
    models = MODEL_CATALOG.get(category, {}).get(family, {}).get("models", [])
    keyboard = []
    
    for model in models:
        cost_text = f"💎 {model.get('cost', 0)}" if model.get('cost', 0) > 0 else "Бесплатно"
        keyboard.append([InlineKeyboardButton(
            text=f"{model['name']} [{cost_text}]",
            callback_data=f"set_model:{model['id']}"
        )])
        
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def nano_banana_menu() -> InlineKeyboardMarkup:
    """Меню выбора моделей Nano Banana."""
    models = MODEL_CATALOG.get("gen_nano_banana", {}).get("nano_banana", {}).get("models", [])
    keyboard = []
    
    for model in models:
        # Убираем стоимость для Free
        if "free" in model['id']:
            text = f"🍌 {model['name']}"
        else:
            cost_text = f"💎 {model.get('cost', 0)}"
            text = f"🍌 {model['name']} [{cost_text}]"
            
        keyboard.append([InlineKeyboardButton(
            text=text,
            callback_data=f"set_model:{model['id']}"
        )])
        
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def profile_menu() -> InlineKeyboardMarkup:
    """Меню профиля."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Пополнить баланс", callback_data="open_subscription")],
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
            callback_data=f"tier_{tier_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🪙 Пакеты токенов", callback_data="packet_tokens")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def token_package_menu() -> InlineKeyboardMarkup:
    """Меню покупки пакетов токенов."""
    keyboard = []
    for packet_id, packet_data in TOKEN_PACKAGES.items():
        keyboard.append([InlineKeyboardButton(
            text=f"{packet_data['name']} - {packet_data['price']}₽",
            callback_data=f"buy_packet:{packet_id}"
        )])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="subscriptions")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
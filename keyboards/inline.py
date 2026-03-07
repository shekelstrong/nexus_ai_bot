from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Текст", callback_data="cat:gen_text"),
            InlineKeyboardButton(text="🌐 Perplexity", callback_data="cat:gen_search")
        ],
        [
            InlineKeyboardButton(text="🎨 Изображения", callback_data="cat:gen_image"),
            InlineKeyboardButton(text="🎬 Видео", callback_data="cat:gen_video")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="💎 Подписка", callback_data="subscriptions")
        ],
        [
            InlineKeyboardButton(text="📊 История", callback_data="history"),
            InlineKeyboardButton(text="🎁 Рефералка", callback_data="referrals")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Поддержка", callback_data="support")
        ]
    ])
    return kb

# --- МЕНЮ ОТМЕНЫ / НАЗАД ---
def cancel_generation_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_menu")]
    ])
    return kb

def back_to_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])
    return kb

def image_gen_mode_kb():
    """Клавиатура выбора режима генерации изображения"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 С референсами", callback_data="img_mode:references")],
        [InlineKeyboardButton(text="✍️ Только промпт", callback_data="img_mode:prompt")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])
    return kb

def references_ready_kb():
    """Клавиатура когда референсы загружены"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово, перехожу к промпту", callback_data="references_done")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="back_to_menu")]
    ])
    return kb

# --- ВЫБОР СЕМЕЙСТВА МОДЕЛЕЙ ---
def model_families_menu(category: str):
    from model_config import MODEL_CATALOG

    buttons = []
    families = MODEL_CATALOG.get(category, {})

    # Красивые названия для семейств
    family_titles = {
        # Текстовые
        "openai": "OpenAI (GPT)",
        "anthropic": "Anthropic (Claude)",
        "google": "Google (Gemini)",
        "deepseek": "DeepSeek",
        "meta": "Meta (Llama)",
        "xai": "xAI (Grok)",
        "qwen": "Qwen (Alibaba)",
        "moonshotai": "Moonshot (Kimi)",
        "mistral": "Mistral AI",
        "tngtech": "TNG (Free)",
        # Изображения
        "flux": "Flux",
        "riverflow": "Riverflow",
        "seedream": "Seedream",
        "gemini_image": "Gemini Image",
        # Видео
        "kling": "Kling AI",
        "veo": "Google Veo",
        "wan": "Wan Video",
        "luma": "Luma Dream Machine",
        # Поиск
        "perplexity": "Perplexity Search",
    }

    row = []
    for fam_key, fam_data in families.items():
        fam_name = family_titles.get(fam_key, fam_key.capitalize())
        row.append(InlineKeyboardButton(text=fam_name, callback_data=f"family:{category}:{fam_key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ВЫБОР КОНКРЕТНОЙ МОДЕЛИ ---
def models_list_menu(category: str, family: str):
    from model_config import MODEL_CATALOG
    
    buttons = []
    models = MODEL_CATALOG.get(category, {}).get(family, {}).get("models", [])
    
    for model in models:
        name = f"{model['name']} ({model.get('cost', 1)}🍌)"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"set_model:{model['id']}")])
        
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ПОДПИСКИ ---
def subscription_tiers_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 BASIC (460 токенов)", callback_data="tier:basic")],
        [InlineKeyboardButton(text="⭐ PRO (880 токенов)", callback_data="tier:pro")],
        [InlineKeyboardButton(text="🏆 VIP (1700 токенов)", callback_data="tier:vip")],
        [InlineKeyboardButton(text="💎 ELITE (2600 токенов)", callback_data="tier:elite")],
        [InlineKeyboardButton(text="──────────────────", callback_data="divider")],
        [InlineKeyboardButton(text="🎬 Видео-пакеты", callback_data="packet:video")],
        [InlineKeyboardButton(text="🪙 Доп. токены", callback_data="packet:tokens")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])
    return kb

def token_package_menu():
    """Меню выбора пакетов докупки токенов"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 25 токенов (390₽)", callback_data="buy_packet:tokens_25")],
        [InlineKeyboardButton(text="🪙 50 токенов (590₽)", callback_data="buy_packet:tokens_50")],
        [InlineKeyboardButton(text="🪙 100 токенов (1190₽)", callback_data="buy_packet:tokens_100")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions")]
    ])
    return kb

def video_packet_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 10 генераций (590₽)", callback_data="buy_packet:video_10")],
        [InlineKeyboardButton(text="🎬 25 генераций (1190₽)", callback_data="buy_packet:video_25")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions")]
    ])
    return kb

# ЗАГЛУШКА ДЛЯ AUDIO, чтобы не падал импорт
def audiopacket_menu(): 
    return video_packet_menu() # Возвращаем что-то валидное или пустую

def audio_packet_menu(): # Алиас на всякий случай
    return video_packet_menu()

def payment_methods_menu(item_id: str, amount: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Банковская карта (RF)", callback_data=f"pay:card:{item_id}")],
        [InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data=f"pay:stars:{item_id}")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="subscriptions")]
    ])
    return kb

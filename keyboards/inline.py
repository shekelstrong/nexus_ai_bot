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

# --- ВЫБОР СЕМЕЙСТВА МОДЕЛЕЙ ---
def model_families_menu(category: str):
    from model_config import MODEL_CATALOG
    
    buttons = []
    families = MODEL_CATALOG.get(category, {})
    
    row = []
    for fam_key, fam_data in families.items():
        fam_name = fam_key.capitalize() 
        if fam_key == "openai": fam_name = "OpenAI (GPT)"
        if fam_key == "google": fam_name = "Google (Gemini)"
        if fam_key == "anthropic": fam_name = "Anthropic (Claude)"
        if fam_key == "midjourney": fam_name = "Midjourney Style"
        if fam_key == "flux": fam_name = "Flux & SD"
        if fam_key == "kling": fam_name = "Kling AI"
        if fam_key == "veo": fam_name = "Google Veo"
        if fam_key == "wan": fam_name = "Wan Video"
        if fam_key == "luma": fam_name = "Luma Dream Machine"
        if fam_key == "perplexity": fam_name = "Perplexity Search"
        
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
        [InlineKeyboardButton(text="💎 Premium", callback_data="tier:premium")],
        [InlineKeyboardButton(text="💎 Premium X2", callback_data="tier:premium_x2")],
        [InlineKeyboardButton(text="🎬 Видео-пакеты", callback_data="packet:video")],
        # Если аудио пакетов нет, кнопку можно скрыть или оставить заглушку
        # [InlineKeyboardButton(text="🎵 Пакеты Suno", callback_data="packet:audio")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])
    return kb

def video_packet_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 10 генераций (290₽)", callback_data="buy_packet:video_10")],
        [InlineKeyboardButton(text="🎬 50 генераций (990₽)", callback_data="buy_packet:video_50")],
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

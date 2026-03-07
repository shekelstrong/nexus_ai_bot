"""
Обработчики уведомлений для администраторов.
- Новый пользователь
- Пополнение через Platega
"""

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.logger import logger
from config import ADMIN_IDS


def get_user_link(user_id: int, username: str = None) -> str:
    """Формирует ссылку на пользователя"""
    if username:
        return f"@{username}"
    return f"ID: {user_id}"


async def notify_admin_new_user(
    bot: Bot,
    user_id: int,
    username: str = None,
    referrer_id: int = None,
    referrer_username: str = None,
    referrer_bonus: float = None,
):
    """
    Уведомление админам о новом пользователе.
    
    Args:
        bot: Bot экземпляр
        user_id: Telegram ID нового пользователя
        username: Username нового пользователя
        referrer_id: Telegram ID рефовода
        referrer_username: Username рефовода
        referrer_bonus: Бонус рефовода (если есть)
    """
    user_link = get_user_link(user_id, username)
    
    if referrer_id:
        ref_link = get_user_link(referrer_id, referrer_username)
        bonus_text = f" (+{referrer_bonus:.2f}₽)" if referrer_bonus else ""
        referrer_line = f"\n👥 Рефовод: {ref_link}{bonus_text}"
    else:
        referrer_line = "\n👥 Рефовод: Нет"
    
    message = (
        f"🆕 <b>Новый пользователь!</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Профиль: {user_link}{referrer_line}"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")


async def notify_admin_payment(
    bot: Bot,
    user_id: int,
    username: str = None,
    tokens: int = 0,
    video: int = 0,
    amount_rub: float = 0,
    referrer_id: int = None,
    referrer_username: str = None,
    referrer_bonus: float = None,
):
    """
    Уведомление админам о пополнении через Platega.
    
    Args:
        bot: Bot экземпляр
        user_id: Telegram ID пользователя
        username: Username пользователя
        tokens: Количество токенов
        video: Количество видео-генераций
        amount_rub: Сумма платежа
        referrer_id: Telegram ID рефовода
        referrer_username: Username рефовода
        referrer_bonus: Бонус рефовода
    """
    user_link = get_user_link(user_id, username)
    
    # Формируем строку о начислениях
    items = []
    if tokens > 0:
        items.append(f"🪙 {tokens} токенов")
    if video > 0:
        items.append(f"🎬 {video} видео")
    
    items_str = ", ".join(items) if items else "—"
    
    # Рефовод
    if referrer_id:
        ref_link = get_user_link(referrer_id, referrer_username)
        bonus_text = f" (+{referrer_bonus:.2f}₽)" if referrer_bonus else ""
        referrer_line = f"\n👥 Рефовод: {ref_link}{bonus_text}"
    else:
        referrer_line = "\n👥 Рефовод: Нет"
    
    message = (
        f"💰 <b>Пополнение через Platega!</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Профиль: {user_link}\n"
        f"💎 Начислено: {items_str}\n"
        f"💵 Сумма: <b>{amount_rub:.2f}₽</b>{referrer_line}"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")


async def notify_referrer_new_referral(
    bot: Bot,
    referrer_id: int,
    new_user_id: int,
    new_user_username: str = None,
    welcome_bonus: float = None,
):
    """
    Уведомление рефоводу о новом реферале.
    
    Args:
        bot: Bot экземпляр
        referrer_id: Telegram ID рефовода
        new_user_id: Telegram ID нового пользователя
        new_user_username: Username нового пользователя
        welcome_bonus: Приветственный бонус (если есть)
    """
    new_user_link = get_user_link(new_user_id, new_user_username)
    
    bonus_text = ""
    if welcome_bonus and welcome_bonus > 0:
        bonus_text = f"\n\n🎁 Вам начислен бонус: <b>{welcome_bonus:.2f}₽</b> (15% от первого пополнения)"
    
    message = (
        f"🎉 <b>Новый реферал!</b>\n\n"
        f"🆔 ID: <code>{new_user_id}</code>\n"
        f"👤 Профиль: {new_user_link}{bonus_text}"
    )
    
    try:
        await bot.send_message(referrer_id, message, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to notify referrer {referrer_id}: {e}")


async def notify_user_purchase(
    bot: Bot,
    user_id: int,
    tokens: int = 0,
    video: int = 0,
    amount_rub: float = 0,
    duration_days: int = 0,
):
    """
    Уведомление пользователю о успешной покупке.
    
    Args:
        bot: Bot экземпляр
        user_id: Telegram ID пользователя
        tokens: Количество токенов
        video: Количество видео-генераций
        amount_rub: Сумма платежа
        duration_days: Срок действия (дней)
    """
    # Формируем строку о начислениях
    items = []
    if tokens > 0:
        if duration_days > 0:
            daily_tokens = tokens // duration_days if duration_days else 0
            items.append(f"🪙 <b>{tokens} токенов</b> ({daily_tokens} в день)")
        else:
            items.append(f"🪙 <b>{tokens} токенов</b> (бессрочно)")
    if video > 0:
        items.append(f"🎬 <b>{video} видео</b> (бессрочно)")
    
    items_str = "\n".join(items) if items else "—"
    
    duration_text = f"\n⏳ Срок: <b>{duration_days} дней</b>" if duration_days > 0 else ""
    
    message = (
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"💎 Начислено:\n{items_str}{duration_text}\n"
        f"💵 Сумма: <b>{amount_rub:.2f}₽</b>\n\n"
        f"Спасибо за покупку! 🎉"
    )
    
    try:
        await bot.send_message(user_id, message, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to notify user {user_id}: {e}")

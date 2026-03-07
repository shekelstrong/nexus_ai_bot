from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SubscriptionTier
from keyboards.inline import (
    subscription_tiers_menu,
    video_packet_menu,
    token_package_menu,
)
from services.platega_client import create_invoice
from services.payments import (
    SUBSCRIPTION_PLANS,
    PACKETS,
    process_platega_payment,
    get_purchase_details,
)
from handlers.admin.notifications import notify_admin_payment, notify_user_purchase
from utils.logger import logger


router = Router(name="payment_router")


@router.callback_query(F.data == "subscriptions")
async def show_subscriptions(cb: CallbackQuery):
    """
    Показываем общее меню тарифов.
    """
    text = (
        "💎 <b>Тарифные планы NexusAI</b>\n\n"
        "📋 <b>Подписки (ежемесячно):</b>\n"
        "• BASIC: 460 токенов/месяц\n"
        "• PRO: 880 токенов/месяц\n"
        "• VIP: 1700 токенов/месяц\n"
        "• ELITE: 2600 токенов/месяц\n\n"
        "🛒 <b>Пакеты (бессрочно):</b>\n"
        "• Токены: 25/50/100\n"
        "• Видео: 10/25 генераций\n\n"
        "👇 <b>Выберите раздел:</b>"
    )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=subscription_tiers_menu(),
    )
    await cb.answer()


@router.callback_query((F.data.startswith("tier_")) | (F.data.startswith("tier:")))
async def tier_selected(cb: CallbackQuery, session: AsyncSession):
    """
    Показываем подробное описание выбранного тарифа и создаем платеж.
    """
    tier_name = cb.data.split("_", 1)[1] if cb.data.startswith("tier_") else cb.data.split(":", 1)[1]
    try:
        tier = SubscriptionTier(tier_name.upper())
    except ValueError:
        await cb.answer("Некорректный тариф", show_alert=True)
        return

    plan = SUBSCRIPTION_PLANS[tier]
    daily_tokens = plan["tokens"] // 30 if plan["tokens"] > 0 else 0
    
    text = (
        f"💎 <b>{tier.value} | МЕСЯЦ</b>\n\n"
        f"📦 <b>Токены:</b> {plan['tokens']} ({daily_tokens} в день)\n"
        f"⏳ <b>Срок:</b> 30 дней\n\n"
        f"✅ <b>Возможности:</b>\n"
        f"• Доступ ко всем текстовым моделям\n"
        f"• Генерация изображений с референсами\n"
        f"• Поиск в интернете (Perplexity)\n"
        f"• Работа с документами\n\n"
        f"💰 <b>Стоимость: {plan['price_rub']} ₽</b>"
    )
    
    # Создаем платеж Platega
    order_id = f"tier_{tier_name}_{cb.from_user.id}"
    invoice_url = await create_invoice(
        amount_rub=plan["price_rub"],
        order_id=order_id,
        user_id=cb.from_user.id,
        description=f"Subscription {tier.value}"
    )
    
    if not invoice_url:
        await cb.answer("Ошибка создания платежа", show_alert=True)
        return

    # Клавиатура с оплатой
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить картой", url=invoice_url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions")]
    ])

    await cb.message.edit_text(
        text + "\n\n👇 <b>Нажмите кнопку для оплаты:</b>",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query((F.data == "packet_video") | (F.data == "packet:video"))
async def packet_video_selected(cb: CallbackQuery):
    """Меню выбора видео-пакета"""
    text = (
        "🎬 <b>ВИДЕО-ПАКЕТЫ</b>\n\n"
        "Генерация видео на нейросетях:\n"
        "• Kling AI\n"
        "• Google Veo 3.1\n"
        "• Wan Video\n\n"
        "✨ <b>Возможности:</b>\n"
        "• Text-to-Video\n"
        "• Image-to-Video\n"
        "• Motion Control\n\n"
        "👇 <b>Выберите размер пакета:</b>"
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=video_packet_menu(),
    )
    await cb.answer()


@router.callback_query((F.data == "packet_tokens") | (F.data == "packet:tokens"))
async def packet_tokens_selected(cb: CallbackQuery):
    """Меню выбора пакета токенов"""
    text = (
        "🪙 <b>ПАКЕТЫ ТОКЕНОВ</b>\n\n"
        "Дополнительные токены для генерации:\n"
        "• Текст: 1-20 токенов за запрос\n"
        "• Изображения: 1-8 токенов за генерацию\n"
        "• Поиск: 1-6 токенов за запрос\n\n"
        "⏳ <b>Токены не сгорают!</b>\n\n"
        "👇 <b>Выберите размер пакета:</b>"
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=token_package_menu(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("buy_packet:"))
async def buy_packet_handler(cb: CallbackQuery, session: AsyncSession):
    packet_id = cb.data.split(":", 1)[1]
    packet = PACKETS.get(packet_id)
    if not packet:
        await cb.answer("Пакет не найден", show_alert=True)
        return

    amount = packet["price_rub"]
    packet_type = packet.get("type", "tokens")
    
    # Определяем тип для оплаты
    pay_type = "video" if packet_type == "video" else "tokens"
    
    # Создаем платеж Platega
    order_id = f"{pay_type}_{packet_id}_{cb.from_user.id}"
    invoice_url = await create_invoice(
        amount_rub=amount,
        order_id=order_id,
        user_id=cb.from_user.id,
        description=f"Packet {packet['name']}"
    )
    
    if not invoice_url:
        await cb.answer("Ошибка создания платежа", show_alert=True)
        return

    # Клавиатура с оплатой
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить картой", url=invoice_url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions")]
    ])

    await cb.message.edit_text(
        f"✅ Вы выбрали: <b>{packet['name']}</b>\n"
        f"💰 К оплате: <b>{amount} ₽</b>\n\n"
        f"👇 <b>Нажмите кнопку для оплаты:</b>",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("pay_success:"))
async def pay_success_handler(cb: CallbackQuery, session: AsyncSession):
    """
    Обработчик успешной оплаты (вызывается после возврата из Platega).
    Формат: pay_success:{order_id}
    """
    order_id = cb.data.split(":", 1)[1]
    
    # Парсим order_id
    parts = order_id.split("_")
    if len(parts) < 3:
        await cb.answer("Ошибка обработки платежа", show_alert=True)
        return
    
    item_type = parts[0]
    item_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else parts[0]
    
    # Получаем детали покупки
    details = get_purchase_details(item_type, item_id)
    
    text = (
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"💎 Начислено:\n"
    )
    
    if details['tokens'] > 0:
        if details['duration_days'] > 0:
            daily = details['tokens'] // details['duration_days']
            text += f"🪙 <b>{details['tokens']} токенов</b> ({daily} в день)\n"
        else:
            text += f"🪙 <b>{details['tokens']} токенов</b> (бессрочно)\n"
    
    if details['video'] > 0:
        text += f"🎬 <b>{details['video']} видео</b> (бессрочно)\n"
    
    if details['duration_days'] > 0:
        text += f"\n⏳ Срок: <b>{details['duration_days']} дней</b>"
    
    text += "\n\nСпасибо за покупку! 🎉"
    
    await cb.message.answer(text, parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("pay_failed:"))
async def pay_failed_handler(cb: CallbackQuery):
    """
    Обработчик неудачной оплаты.
    """
    await cb.message.answer(
        "❌ <b>Оплата не прошла</b>\n\n"
        "Попробуйте еще раз или выберите другой способ оплаты.",
        parse_mode="HTML"
    )
    await cb.answer()

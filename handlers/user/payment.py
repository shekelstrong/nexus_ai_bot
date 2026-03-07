from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession


from database.models import SubscriptionTier
from keyboards.inline import (
    subscription_tiers_menu,
    payment_methods_menu,
    video_packet_menu,
    token_package_menu,
)
from services.payments import (
    SUBSCRIPTION_PLANS,
    PACKETS,
    send_stars_invoice,
    handle_pre_checkout,
    handle_successful_payment,
)
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
async def tier_selected(cb: CallbackQuery):
    """
    Показываем подробное описание выбранного тарифа.
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
    amount = plan["price_rub"]

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=payment_methods_menu(f"tier_{tier.value}", amount),
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
async def buy_packet_handler(cb: CallbackQuery):
    packet_id = cb.data.split(":", 1)[1]
    packet = PACKETS.get(packet_id)
    if not packet:
        await cb.answer("Пакет не найден", show_alert=True)
        return

    amount = packet["price_rub"]
    packet_type = packet.get("type", "tokens")
    
    # Определяем тип для оплаты
    pay_type = "video" if packet_type == "video" else "tokens"
    
    await cb.message.edit_text(
        f"✅ Вы выбрали: <b>{packet['name']}</b>\n"
        f"💰 К оплате: <b>{amount} ₽</b>\n\n"
        "Выберите способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_methods_menu(f"packet_{pay_type}_{packet_id}", amount),
    )
    await cb.answer()


@router.callback_query((F.data.startswith("pay_stars_")) | (F.data.startswith("pay:stars:")))
async def pay_stars(cb: CallbackQuery, session: AsyncSession):
    if cb.data.startswith("pay_stars_"):
        parts = cb.data.split("_")
        if len(parts) < 4:
            await cb.answer("Ошибка формата", show_alert=True)
            return
        kind = parts[2]
        item_token = parts[3:]
    else:
        parts = cb.data.split(":")
        if len(parts) < 3:
            await cb.answer("Ошибка формата", show_alert=True)
            return
        kind = parts[2]
        item_token = parts[3:]
    
    try:
        if kind == "tier":
            tier_name = item_token[0] if item_token else ""
            await send_stars_invoice(
                bot=cb.bot,
                session=session,
                chat_id=cb.message.chat.id,
                telegram_user_id=cb.from_user.id,
                item_type="tier",
                item_id=tier_name,
            )
        elif kind == "packet":
            # Формат: packet_tokens_tokens_25 или packet_video_video_10
            if len(item_token) >= 3:
                packet_type = item_token[0]  # tokens или video
                packet_id = item_token[1] + "_" + item_token[2] if len(item_token) > 2 else item_token[1]
            else:
                packet_id = item_token[0] if item_token else ""
                packet_type = "tokens"
            
            await send_stars_invoice(
                bot=cb.bot,
                session=session,
                chat_id=cb.message.chat.id,
                telegram_user_id=cb.from_user.id,
                item_type=packet_type,
                item_id=packet_id,
            )
        else:
            await cb.answer("Неизвестный тип оплаты", show_alert=True)
            return

        await cb.answer("Инвойс отправлен ⭐")
    except Exception as e:
        logger.exception("Failed to send Stars invoice")
        await cb.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_crypto(cb: CallbackQuery):
    await cb.answer("В разработке...", show_alert=True)


@router.callback_query(F.data.startswith("pay_fiat_"))
async def pay_fiat(cb: CallbackQuery):
    await cb.answer("В разработке...", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: PreCheckoutQuery):
    await handle_pre_checkout(pre_checkout, pre_checkout.bot)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, session: AsyncSession):
    payment = message.successful_payment
    await handle_successful_payment(
        session=session,
        telegram_user_id=message.from_user.id,
        payload=payment.invoice_payload,
        total_amount=payment.total_amount,
        currency=payment.currency,
    )
    await message.answer(
        "✅ <b>Оплата успешна!</b>\n\nСпасибо за покупку! Лимиты обновлены.",
        parse_mode="HTML",
    )
    logger.info(f"Successful payment from {message.from_user.id}: {payment.total_amount} {payment.currency}")

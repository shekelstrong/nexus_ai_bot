from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession


from database.models import SubscriptionTier
from keyboards.inline import (
    subscription_tiers_menu,
    payment_methods_menu,
    video_packet_menu,
    audio_packet_menu,
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
        "Выберите интересующий вас план или пакет, чтобы узнать подробности и условия:\n\n"
        "👇 <b>Нажмите на кнопку ниже:</b>"
    )


    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=subscription_tiers_menu(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("tier_") | F.data.startswith("tier:"))
async def tier_selected(cb: CallbackQuery):
    """
    Показываем подробное описание выбранного тарифа.
    """
    tier_name = cb.data.split("_", 1)[1] if cb.data.startswith("tier_") else cb.data.split(":", 1)[1]
    try:
        tier = SubscriptionTier(tier_name)
    except ValueError:
        await cb.answer("Некорректный тариф", show_alert=True)
        return


    if tier == SubscriptionTier.PREMIUM:
        # Описание для ПРЕМИУМ
        plan = SUBSCRIPTION_PLANS[SubscriptionTier.PREMIUM]
        text = (
            "💎 <b>ПРЕМИУМ | МЕСЯЦ</b>\n\n"
            "🔼 <b>Лимит запросов:</b> 50 в день\n\n"
            "✅ <b>Доступные возможности:</b>\n"
            "• GPT-5 mini | GPT-4o mini\n"
            "• DeepSeek-V3.2 | Gemini 3 Flash\n"
            "• Интернет-поиск Perplexity\n"
            "• Распознавание изображений\n"
            "• 25 генераций изображений\n\n"
            "🚀 <b>Расширенные модели:</b>\n"
            "• GPT-5.2 | GPT-4.1 | OpenAI o3\n"
            "• Gemini 3 Pro | Claude 4.5\n"
            "• Работа с документами\n"
            "• Голосовые ответы\n\n"
            f"💰 <b>Стоимость: {plan['price_rub']} ₽</b>"
        )
        amount = plan["price_rub"]
        
    elif tier == SubscriptionTier.PREMIUM_X2:
        # Описание для ПРЕМИУМ X2
        plan = SUBSCRIPTION_PLANS[SubscriptionTier.PREMIUM_X2]
        text = (
            "💎 <b>ПРЕМИУМ X2 | МЕСЯЦ</b>\n\n"
            "⏫ <b>Лимит запросов:</b> 100 в день\n\n"
            "✅ <b>Включает все опции тарифа «Премиум»:</b>\n"
            "• Топовые нейросети (GPT-5, Claude 4.5, и др.)\n"
            "• Интернет-поиск и работа с документами\n"
            "• Генерация изображений и голосовые ответы\n\n"
            f"💰 <b>Стоимость: {plan['price_rub']} ₽</b>"
        )
        amount = plan["price_rub"]
        
    else:
        await cb.answer("Описание для этого тарифа не готово", show_alert=True)
        return


    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=payment_methods_menu(f"tier_{tier.value}", amount),
    )
    await cb.answer()


@router.callback_query(F.data == "packet_video" | (F.data == "packet:video"))
async def packet_video_selected(cb: CallbackQuery):
    """Меню выбора видео-пакета"""
    text = (
        "🎬 <b>ВИДЕО | ПАКЕТ</b>\n\n"
        "От 10 до 50 генераций (на выбор)\n\n"
        "✅ <b>Модели:</b>\n"
        "• Veo 3.1 | Sora 2 | Kling | Hailuo | Pika\n\n"
        "✨ <b>Возможности:</b>\n"
        "• Видео на основе изображений\n"
        "• Креативные видео-эффекты\n\n"
        "💰 <b>Стоимость:</b> от 290 ₽ (10 генераций) до 990 ₽ (50 генераций)\n\n"
        "👇 <b>Выберите размер пакета:</b>"
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=video_packet_menu(),
    )
    await cb.answer()


@router.callback_query(F.data == "packet_audio" | (F.data == "packet:audio"))
async def packet_audio_selected(cb: CallbackQuery):
    """Меню выбора аудио-пакета"""
    text = (
        "🎸 <b>ПЕСНИ SUNO | ПАКЕТ</b>\n\n"
        "От 20 до 100 генераций (на выбор)\n\n"
        "✅ <b>Модель:</b> Suno V5\n"
        "✨ <b>Возможности:</b>\n"
        "• Свои стихи или генерация текста с AI\n"
        "• Создание полных треков\n\n"
        "💰 <b>Стоимость:</b> от 390 ₽ (20 генераций) до 990 ₽ (100 генераций)\n\n"
        "👇 <b>Выберите размер пакета:</b>"
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=audio_packet_menu(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("buy_video_") | F.data.startswith("buy_packet:video_"))
async def buy_video_packet(cb: CallbackQuery):
    if cb.data.startswith("buy_video_"):
        packet_id = "video_" + cb.data.split("_", 2)[2]
    else:
        packet_id = cb.data.split(":", 1)[1]
    packet = PACKETS.get(packet_id)
    if not packet:
        await cb.answer("Пакет не найден", show_alert=True)
        return


    amount = packet["price_rub"]
    await cb.message.edit_text(
        f"🎬 Вы выбрали: <b>{packet['name']}</b>\n"
        f"💰 К оплате: <b>{amount} ₽</b>\n\n"
        "Выберите способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_methods_menu(f"packet_{packet_id}", amount),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("buy_audio_") | F.data.startswith("buy_packet:audio_"))
async def buy_audio_packet(cb: CallbackQuery):
    if cb.data.startswith("buy_audio_"):
        packet_id = "audio_" + cb.data.split("_", 2)[2]
    else:
        packet_id = cb.data.split(":", 1)[1]
    packet = PACKETS.get(packet_id)
    if not packet:
        await cb.answer("Пакет не найден", show_alert=True)
        return


    amount = packet["price_rub"]
    await cb.message.edit_text(
        f"🎸 Вы выбрали: <b>{packet['name']}</b>\n"
        f"💰 К оплате: <b>{amount} ₽</b>\n\n"
        "Выберите способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_methods_menu(f"packet_{packet_id}", amount),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("pay_stars_") | F.data.startswith("pay:stars:"))
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
            if cb.data.startswith("pay_stars_"):
                packet_id = item_token[0] + "_" + item_token[1]
            else:
                packet_id = item_token[0] if item_token else ""
            await send_stars_invoice(
                bot=cb.bot,
                session=session,
                chat_id=cb.message.chat.id,
                telegram_user_id=cb.from_user.id,
                item_type="packet",
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

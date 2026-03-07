"""
HTTP сервер для обработки вебхуков от Platega.
Запускается вместе с ботом в основном процессе.
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable

from aiohttp import web

from database.db import db
from database.session import async_session_maker
from services.payments import process_platega_payment
from utils.logger import setup_logger

logger = setup_logger()


class WebhookServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.bot = None
        
        # Регистрируем роуты
        self.app.router.add_post('/webhook/platega', self.handle_platega_webhook)
        self.app.router.add_get('/health', self.handle_health)
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({"status": "ok"})
    
    async def handle_platega_webhook(self, request: web.Request) -> web.Response:
        """
        Обработка вебхука от Platega.
        
        Ожидаемые данные:
        {
            "status": "CONFIRMED",
            "payload": "order_id",
            "amount": 100,
            "currency": "RUB"
        }
        """
        try:
            data = await request.json()
            logger.info(f"💰 PLATEGA WEBHOOK: {data}")
            
            status = str(data.get("status")).upper()
            if status != "CONFIRMED":
                logger.info(f"Ignoring payment status: {status}")
                return web.json_response({"status": "ignored"})
            
            order_id = data.get("payload")
            amount = Decimal(str(data.get("amount", 0)))
            currency = data.get("currency", "RUB")
            
            if not order_id:
                logger.error("No payload in webhook")
                return web.json_response({"status": "error", "msg": "no payload"}, status=400)
            
            # Обрабатываем платеж
            async with async_session_maker() as session:
                # Парсим order_id: format "tokens_25_12345" или "tier_BASIC_12345"
                parts = str(order_id).split("_")
                
                if len(parts) < 3:
                    logger.error(f"Invalid order_id format: {order_id}")
                    return web.json_response({"status": "error"}, status=400)
                
                item_type = parts[0]
                item_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else parts[0]
                user_telegram_id = int(parts[-1])
                
                # Находим пользователя
                from database.models import User
                from sqlalchemy import select
                
                res = await session.execute(select(User).where(User.telegram_id == user_telegram_id))
                user = res.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User not found: {user_telegram_id}")
                    return web.json_response({"status": "error"}, status=404)
                
                # Создаем транзакцию
                from services.payments import create_pending_transaction, activate_subscription, activate_packet, SUBSCRIPTION_PLANS, PACKETS
                from database.models import TransactionType, TransactionStatus, SubscriptionTier
                
                tx = await create_pending_transaction(
                    session=session,
                    user_id=user.id,
                    amount=amount,
                    currency="RUB",
                    tx_type=TransactionType.TOKEN_PURCHASE,
                    payment_system="platega",
                    extra_data={"item_type": item_type, "item_id": item_id},
                )
                
                # Активируем товар
                tokens_added = 0
                video_added = 0
                
                if item_type == "tier":
                    tier = SubscriptionTier(item_id.upper())
                    plan = SUBSCRIPTION_PLANS[tier]
                    tokens_added = plan["tokens"]
                    await activate_subscription(session, user.id, tier)
                    
                elif item_type == "tokens":
                    packet = PACKETS.get(item_id)
                    if packet:
                        tokens_added = packet.get("tokens", 0)
                        await activate_packet(session, user.id, item_id)
                        
                elif item_type == "video":
                    packet = PACKETS.get(item_id)
                    if packet:
                        video_added = packet.get("generations", 0)
                        await activate_packet(session, user.id, item_id)
                
                # Обновляем транзакцию
                tx.status = TransactionStatus.SUCCESS
                tx.completed_at = datetime.utcnow()
                await session.commit()
                
                # Обработка рефералов (15%/10%/5%)
                from services.payments import get_referrer_chain, REF_LEVELS

                chain = await get_referrer_chain(session, user.id)
                total_ref_bonus = Decimal("0")

                for ref_data in chain:
                    referrer = ref_data['user']
                    level = ref_data['level']
                    bonus_percent = ref_data['bonus_percent']

                    bonus = amount * Decimal(str(bonus_percent))
                    total_ref_bonus += bonus

                    # Начисляем бонус
                    referrer.referral_balance += bonus

                    # Уведомляем реферера
                    try:
                        await self.bot.send_message(
                            referrer.telegram_id,
                            f"💸 <b>Реферальное начисление!</b>\n\n"
                            f"Ваш реферал (ID: {user_telegram_id}) пополнил баланс.\n"
                            f"Вам начислено: <b>+{bonus:.2f}₽</b> ({level} уровень, {bonus_percent*100:.0f}%)\n\n"
                            f"Реферальный баланс: {referrer.referral_balance}₽",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to notify referrer {referrer.telegram_id}: {e}")

                await session.commit()

                # Уведомляем пользователя
                items = []
                if tokens_added > 0:
                    items.append(f"🪙 {tokens_added} токенов")
                if video_added > 0:
                    items.append(f"🎬 {video_added} видео")

                items_str = ", ".join(items) if items else "—"

                duration_text = ""
                if item_type == "tier":
                    plan = SUBSCRIPTION_PLANS.get(SubscriptionTier(item_id.upper()))
                    if plan and plan["days"] > 0:
                        duration_text = f"\n⏳ Срок: <b>{plan['days']} дней</b>"

                await self.bot.send_message(
                    user_telegram_id,
                    f"✅ <b>Оплата прошла успешно!</b>\n\n"
                    f"💎 Начислено: <b>{items_str}</b>{duration_text}\n"
                    f"💰 Сумма: <b>{amount:.2f} {currency}</b> (Platega)\n\n"
                    f"Спасибо за покупку! 🎉",
                    parse_mode="HTML"
                )

                # Уведомляем админам
                from config import ADMIN_IDS

                referrer_info = None
                if user.referrer_id:
                    ref_res = await session.execute(
                        select(User).where(User.id == user.referrer_id)
                    )
                    referrer = ref_res.scalar_one_or_none()
                    if referrer:
                        referrer_info = {
                            'id': referrer.telegram_id,
                            'username': referrer.username,
                            'bonus': amount * Decimal("0.15"),
                        }

                user_display = f" @{user.username}" if user.username else f"ID: {user_telegram_id}"
                referrer_line = ""

                if referrer_info:
                    ref_link = f"@{referrer_info['username']}" if referrer_info['username'] else f"ID: {referrer_info['id']}"
                    referrer_line = f"\n👥 Рефовод: {ref_link} (+{referrer_info['bonus']:.2f}₽)"
                else:
                    referrer_line = "\n👥 Рефовод: Нет"

                admin_msg = (
                    f"✅ Оплата: {amount:.2f} {currency}\n"
                    f"Пользователь: {user_display}\n"
                    f"Начислено: {items_str}{referrer_line}"
                )

                for admin_id in ADMIN_IDS:
                    try:
                        await self.bot.send_message(admin_id, admin_msg)
                    except Exception as e:
                        logger.warning(f"Failed to notify admin {admin_id}: {e}")

                logger.info(
                    f"✅ Platega payment: User {user_telegram_id} +{tokens_added} tokens, "
                    f"+{video_added} video | Amount: {amount} RUB | "
                    f"Ref bonus: {total_ref_bonus} RUB"
                )

                return web.json_response({"status": "ok"})
                    
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook")
            return web.json_response({"status": "error", "msg": "invalid json"}, status=400)
        except Exception as e:
            logger.exception(f"Webhook error: {e}")
            return web.json_response({"status": "error", "msg": str(e)}, status=500)
    
    async def start(self, bot):
        """Запуск сервера"""
        self.bot = bot
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"🌐 Webhook server started on http://{self.host}:{self.port}")
        logger.info(f"   Platega webhook: POST /webhook/platega")
        logger.info(f"   Health check: GET /health")
        return runner
    
    async def stop(self, runner):
        """Остановка сервера"""
        await runner.cleanup()
        logger.info("Webhook server stopped")


# Глобальный экземпляр
webhook_server = WebhookServer(port=8080)

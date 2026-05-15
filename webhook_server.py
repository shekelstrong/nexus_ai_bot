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
from config import WEB_PORT

logger = setup_logger()

class WebhookServer:
    def __init__(self, host: str = "0.0.0.0", port: int = None):
        self.host = host
        self.port = port if port is not None else WEB_PORT
        self.app = web.Application()
        self.bot = None

        # Регистрируем роуты
        self.app.router.add_post('/webhook/platega', self.handle_platega_webhook)
        self.app.router.add_get('/health', self.handle_health)
        # Роуты для возврата пользователя после оплаты
        self.app.router.add_get('/pay_success', self.handle_pay_success)
        self.app.router.add_get('/pay_failed', self.handle_pay_failed)
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({"status": "ok"})

    async def handle_pay_success(self, request: web.Request) -> web.Response:
        """
        Обработчик возврата пользователя после успешной оплаты.
        Перенаправляет в бота с параметром для отображения успеха.
        """
        order_id = request.query.get('order_id')
        
        if order_id:
            redirect_url = f"https://t.me/{(await self.bot.get_me()).username}?start=pay_success_{order_id}"
        else:
            redirect_url = f"https://t.me/{(await self.bot.get_me()).username}"
        
        raise web.HTTPSeeOther(redirect_url)

    async def handle_pay_failed(self, request: web.Request) -> web.Response:
        """
        Обработчик возврата пользователя после неудачной оплаты.
        Перенаправляет в бота с параметром для отображения ошибки.
        """
        redirect_url = f"https://t.me/{(await self.bot.get_me()).username}?start=pay_failed"
        raise web.HTTPSeeOther(redirect_url)
    
    async def handle_platega_webhook(self, request: web.Request) -> web.Response:
        """
        Обработка вебхука от Platega.
        """
        try:
            try:
                data = await request.json()
            except json.JSONDecodeError:
                form_data = await request.post()
                data = dict(form_data)
                logger.info(f"💰 PLATEGA WEBHOOK (form-data): {data}")

            logger.info(f"💰 PLATEGA WEBHOOK: {data}")

            status = str(data.get("status") or data.get("Status") or data.get("STATUS", "")).upper()

            if status not in ("CONFIRMED", "SUCCESS", "PAID", "COMPLETED"):
                logger.info(f"Ignoring payment status: {status}")
                return web.json_response({"status": "ignored"})

            order_id = data.get("payload") or data.get("order_id") or data.get("orderId") or data.get("merchant_order_id")
            amount = Decimal(str(data.get("amount") or data.get("Amount") or data.get("total") or 0))
            currency = data.get("currency") or data.get("Currency") or "RUB"

            if not order_id:
                logger.error("No payload/order_id in webhook data")
                return web.json_response({"status": "error", "msg": "no payload"}, status=400)

            await self.process_payment(order_id, amount, currency, "Platega")

            return web.json_response({"status": "ok"})

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook")
            return web.json_response({"status": "error", "msg": "invalid json"}, status=400)
        except Exception as e:
            logger.exception(f"Webhook error: {e}")
            return web.json_response({"status": "error", "msg": str(e)}, status=500)

    async def process_payment(self, order_id, amount, currency, method_name):
        """
        Единая функция обработки платежа.
        """
        from database.models import User
        from sqlalchemy import select
        from services.payments import (
            create_pending_transaction,
            activate_subscription,
            activate_packet,
            SUBSCRIPTION_PLANS,
            PACKETS,
            get_referrer_chain,
            REF_LEVELS,
        )
        from database.models import TransactionType, TransactionStatus, SubscriptionTier

        async with async_session_maker() as session:
            parts = str(order_id).split("_")

            if len(parts) < 3:
                logger.error(f"Invalid order_id format: {order_id}")
                return

            item_type = parts[0]
            user_telegram_id = int(parts[-1])
            
            if len(parts) == 3:
                # tokens_50_12345 → item_type=tokens, item_id=tokens_50
                if item_type == "tokens":
                    item_id = f"{parts[0]}_{parts[1]}"
                else:
                    item_id = parts[1]
            else:
                item_id = "_".join(parts[1:-1])
            
            logger.info(f"Payment: order_id={order_id}, item_type={item_type}, item_id={item_id}, user={user_telegram_id}")

            res = await session.execute(select(User).where(User.telegram_id == user_telegram_id))
            user = res.scalar_one_or_none()

            if not user:
                logger.error(f"User not found: {user_telegram_id}")
                return

            tx = await create_pending_transaction(
                session=session,
                user_id=user.id,
                amount=amount,
                currency="RUB",
                tx_type=TransactionType.TOKEN_PURCHASE,
                payment_system="platega",
                extra_data={"item_type": item_type, "item_id": item_id},
            )

            tokens_added = 0

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

            tx.status = TransactionStatus.SUCCESS
            tx.completed_at = datetime.utcnow()
            await session.commit()

            chain = await get_referrer_chain(session, user.id)
            total_ref_bonus = Decimal("0")

            for ref_data in chain:
                referrer = ref_data['user']
                level = ref_data['level']
                bonus_percent = ref_data['bonus_percent']

                bonus = amount * Decimal(str(bonus_percent))
                total_ref_bonus += bonus

                referrer.referral_balance += bonus

                try:
                    await self.bot.send_message(
                        referrer.telegram_id,
                        f"💸 <b>Реферальное начисление!</b>\n\n"
                        f"Ваш реферал пополнил баланс.\n"
                        f"Вам начислено: <b>+{bonus:.2f}₽</b> ({level} уровень, {bonus_percent*100:.0f}%)\n\n"
                        f"Реферальный баланс: {referrer.referral_balance}₽",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify referrer {referrer.telegram_id}: {e}")

            await session.commit()

            items_str = f"🪙 {tokens_added} токенов" if tokens_added > 0 else "—"

            duration_text = ""
            if item_type == "tier":
                plan = SUBSCRIPTION_PLANS.get(SubscriptionTier(item_id.upper()))
                if plan and plan["days"] > 0:
                    duration_text = f"\n⏳ Срок: <b>{plan['days']} дней</b>"

            try:
                await self.bot.send_message(
                    user_telegram_id,
                    f"✅ <b>Оплата прошла успешно!</b>\n\n"
                    f"💎 Начислено: <b>{items_str}</b>{duration_text}\n"
                    f"💰 Сумма: <b>{amount:.2f} {currency}</b> (Platega)\n\n"
                    f"Спасибо за покупку! 🎉",
                    parse_mode="HTML"
                )
                logger.info(f"✅ User {user_telegram_id} notified about successful payment")
            except Exception as e:
                logger.error(f"Failed to notify user {user_telegram_id}: {e}")

            logger.info(
                f"✅ Platega payment: User {user_telegram_id} +{tokens_added} tokens | "
                f"Amount: {amount} RUB | "
                f"Ref bonus: {total_ref_bonus} RUB"
            )
    
    async def start(self, bot):
        self.bot = bot
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        from config import SSL_CERT_PATH, SSL_KEY_PATH, BASE_URL
        
        if SSL_CERT_PATH and SSL_KEY_PATH:
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
            site = web.TCPSite(runner, self.host, self.port, ssl_context=ssl_context)
            await site.start()
            protocol = "https"
            logger.info(f"🌐 Webhook server started on https://{self.host}:{self.port} (SSL)")
        else:
            site = web.TCPSite(runner, self.host, self.port)
            await site.start()
            protocol = "http"
            logger.info(f"🌐 Webhook server started on http://{self.host}:{self.port} (no SSL)")
            logger.warning("⚠️ SSL не настроен! Для работы вебхуков от Platega необходим HTTPS.")
        
        if BASE_URL.startswith("http://") or BASE_URL.startswith("https://"):
            webhook_url = f"{BASE_URL}/webhook/platega"
        else:
            webhook_url = f"{protocol}://{BASE_URL}/webhook/platega"
        logger.info(f"   🔗 Platega webhook URL: {webhook_url}")
        logger.info(f"   Health check: GET /health")
        
        return runner
    
    async def stop(self, runner):
        if runner:
            await runner.cleanup()
            logger.info("Webhook server stopped")
        else:
            logger.info("Webhook server: runner is None, skipping cleanup")

webhook_server = WebhookServer()
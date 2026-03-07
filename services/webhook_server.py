"""
HTTP сервер для обработки вебхуков от Platega.
Запускается вместе с ботом в основном процессе.
"""

import asyncio
import json
import logging
from decimal import Decimal
from typing import Callable

from aiohttp import web

from database.db import db
from database.session import async_session_maker
from services.payments import process_platega_payment
from handlers.admin.notifications import notify_admin_payment, notify_user_purchase
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
            
            # Создаем callback для уведомлений
            async def notify_callback(referrer_id: int, level: int, bonus: Decimal):
                try:
                    # Получаем данные о пользователе который оплатил
                    # (нужно распарсить order_id)
                    parts = str(order_id).split("_")
                    if len(parts) >= 3:
                        user_tg_id = int(parts[-1])
                        await self.bot.send_message(
                            referrer_id,
                            f"💸 <b>Реферальное начисление!</b>\n\n"
                            f"Ваш реферал (ID: {user_tg_id}) пополнил баланс.\n"
                            f"Вам начислено: <b>+{bonus:.2f}₽</b> ({level} уровень, {bonus*100/amount:.0f}%)\n\n"
                            f"Реферальный баланс: используйте в профиле.",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.warning(f"Failed to notify referrer {referrer_id}: {e}")
            
            # Обрабатываем платеж
            async with async_session_maker() as session:
                success = await process_platega_payment(
                    session=session,
                    order_id=order_id,
                    amount_rub=amount,
                    notify_callback=notify_callback
                )
                
                if success:
                    # Находим пользователя для отправки уведомлений
                    parts = str(order_id).split("_")
                    if len(parts) >= 3:
                        user_tg_id = int(parts[-1])
                        item_type = parts[0]
                        item_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else parts[0]
                        
                        # Получаем детали покупки
                        from services.payments import get_purchase_details, PACKETS, SUBSCRIPTION_PLANS
                        from database.models import SubscriptionTier
                        
                        details = get_purchase_details(item_type, item_id)
                        
                        # Уведомляем пользователя
                        await notify_user_purchase(
                            bot=self.bot,
                            user_id=user_tg_id,
                            tokens=details.get('tokens', 0),
                            video=details.get('video', 0),
                            amount_rub=float(amount),
                            duration_days=details.get('duration_days', 0)
                        )
                        
                        # Уведомляем админам
                        from database.models import User
                        from sqlalchemy import select
                        
                        res = await session.execute(select(User).where(User.telegram_id == user_tg_id))
                        user = res.scalar_one_or_none()
                        
                        if user:
                            # Получаем рефовода
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
                                        'bonus': amount * Decimal("0.15"),  # 15% первый уровень
                                    }
                            
                            await notify_admin_payment(
                                bot=self.bot,
                                user_id=user_tg_id,
                                username=user.username,
                                tokens=details.get('tokens', 0),
                                video=details.get('video', 0),
                                amount_rub=float(amount),
                                referrer_id=referrer_info['id'] if referrer_info else None,
                                referrer_username=referrer_info['username'] if referrer_info else None,
                                referrer_bonus=float(referrer_info['bonus']) if referrer_info else None,
                            )
                    
                    return web.json_response({"status": "ok"})
                else:
                    logger.error("Failed to process payment")
                    return web.json_response({"status": "error"}, status=500)
                    
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

import aiohttp
import logging
import json
from config import PLATEGA_TOKEN, PLATEGA_MERCHANT_ID, BASE_URL, WEB_PORT

logger = logging.getLogger(__name__)

# Ссылки для возврата после оплаты
# После оплаты пользователь возвращается в бота с параметром для обработки
# order_id будет добавлен при создании платежа
RETURN_URL = f"{BASE_URL}/pay_success"
FAILED_URL = f"{BASE_URL}/pay_failed"


async def create_invoice(amount_rub: int, order_id: str, user_id: int, description: str = ""):
    """
    Создает платеж в Platega.io

    Args:
        amount_rub: Сумма в рублях
        order_id: ID заказа (уникальный, строка формата "tier_BASIC_12345")
        user_id: ID пользователя Telegram
        description: Описание платежа

    Returns:
        str: Ссылка на оплату или None при ошибке
    """
    if not PLATEGA_MERCHANT_ID:
        logger.error("❌ PLATEGA_MERCHANT_ID is missing in config.py!")
        return None

    if not PLATEGA_TOKEN:
        logger.error("❌ PLATEGA_TOKEN is missing in config.py!")
        return None

    # Используем проверенный эндпоинт
    url = "https://app.platega.io/transaction/process"

    headers = {
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Python/3.11 aiohttp/3.10"
    }

    # Формируем payload
    # Важно: order_id передаем и в payload (для вебхука), и в return URL (для возврата)
    return_url_with_order = f"{RETURN_URL}?order_id={order_id}"
    
    payload_data = {
        "paymentMethod": 2,  # Оплата картой
        "paymentDetails": {
            "amount": int(amount_rub),
            "currency": "RUB"
        },
        "description": description if description else f"Order #{order_id}",
        "return": return_url_with_order,
        "failedUrl": FAILED_URL,
        "payload": str(order_id)  # В payload передаем order_id для идентификации в вебхуке
    }

    logger.info(f"📤 Platega Request: {payload_data}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload_data, headers=headers) as resp:
                response_text = await resp.text()
                logger.info(f"📥 Platega Response status: {resp.status}")

                # Попытка 1: Пробуем распарсить JSON (штатный режим)
                try:
                    data = json.loads(response_text)
                except:
                    logger.warning(f"⚠️ Platega ответила не JSON-ом: {response_text}")
                    data = {}

                if resp.status in (200, 201):
                    # Ищем ссылку
                    link = data.get("redirect") or data.get("url") or data.get("payment_url")
                    if link:
                        logger.info(f"✅ Invoice created: {link}")
                        return link
                    else:
                        logger.error(f"❌ Ссылка не найдена в ответе: {data}")
                        return None
                else:
                    logger.error(f"❌ Platega Error ({resp.status}): {response_text}")
                    return None

        except Exception as e:
            logger.error(f"❌ Platega Connection Error: {e}")
            return None

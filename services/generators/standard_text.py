# services/generators/standard_text.py
import aiohttp
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, delete
from config import settings
from utils.logger import logger
from database.models import MessageHistory


class StandardTextGenerator:
    """
    Генератор текста через OpenRouter API с поддержкой долгосрочной памяти.
    """

    # Максимальное количество сообщений в истории (пары user+assistant = 1 единица)
    MAX_HISTORY_MESSAGES = 20

    def __init__(self):
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.key = settings.OPENROUTER_API_KEY

    async def _load_history(
        self,
        session: AsyncSession,
        user_id: int,
        model_id: str
    ) -> List[Dict[str, str]]:
        """
        Загружает историю переписки пользователя с конкретной моделью.
        Возвращает список сообщений в формате [{"role": "user/assistant", "content": "..."}]
        """
        try:
            # Получаем последние MAX_HISTORY_MESSAGES сообщений для этой пары user+model
            result = await session.execute(
                select(MessageHistory)
                .where(MessageHistory.user_id == user_id)
                .where(MessageHistory.model_id == model_id)
                .order_by(desc(MessageHistory.created_at))
                .limit(self.MAX_HISTORY_MESSAGES)
            )
            history_records = result.scalars().all()

            # Переворачиваем, чтобы старые сообщения были первыми
            history_records = list(reversed(history_records))

            messages = []
            for record in history_records:
                # Фильтруем сообщения с пустым content
                if record.content and record.content.strip():
                    messages.append({
                        "role": record.role,
                        "content": record.content
                    })

            logger.info(f"Loaded {len(messages)} history messages for user {user_id}, model {model_id}")
            return messages

        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    async def _save_history(
        self,
        session: AsyncSession,
        user_id: int,
        model_id: str,
        user_message: str,
        assistant_message: str
    ) -> None:
        """
        Сохраняет пару сообщений (запрос + ответ) в историю.
        ВАЖНО: не делает commit, это делает внешний код.
        """
        try:
            # Сохраняем сообщение пользователя
            user_msg = MessageHistory(
                user_id=user_id,
                role="user",
                content=user_message,
                model_id=model_id
            )
            session.add(user_msg)

            # Сохраняем ответ ассистента
            assistant_msg = MessageHistory(
                user_id=user_id,
                role="assistant",
                content=assistant_message,
                model_id=model_id
            )
            session.add(assistant_msg)

            # Очищаем старую историю, если она превышает лимит
            await self._cleanup_old_history(session, user_id, model_id)

            logger.info(f"Prepared 2 history messages for save (user {user_id}, model {model_id})")

        except Exception as e:
            logger.error(f"Error preparing history for save: {e}")
            # Не делаем rollback здесь, это делает внешний код

    async def _cleanup_old_history(
        self,
        session: AsyncSession,
        user_id: int,
        model_id: str
    ) -> None:
        """
        Удаляет старую историю, оставляя только последние MAX_HISTORY_MESSAGES сообщений.
        ВАЖНО: не делает commit, это делает внешний код.
        """
        try:
            # Считаем общее количество сообщений
            count_result = await session.execute(
                select(func.count(MessageHistory.id))
                .where(MessageHistory.user_id == user_id)
                .where(MessageHistory.model_id == model_id)
            )
            total_count = count_result.scalar_one() or 0

            if total_count > self.MAX_HISTORY_MESSAGES:
                # Получаем ID сообщений, которые нужно удалить (самые старые)
                to_delete_count = total_count - self.MAX_HISTORY_MESSAGES

                old_records = await session.execute(
                    select(MessageHistory.id)
                    .where(MessageHistory.user_id == user_id)
                    .where(MessageHistory.model_id == model_id)
                    .order_by(MessageHistory.created_at.asc())
                    .limit(to_delete_count)
                )
                old_ids = [r[0] for r in old_records.all()]

                if old_ids:
                    # Удаляем старые записи
                    await session.execute(
                        delete(MessageHistory)
                        .where(MessageHistory.id.in_(old_ids))
                    )
                    logger.info(f"Prepared cleanup of {len(old_ids)} old history messages")

        except Exception as e:
            logger.error(f"Error preparing cleanup: {e}")

    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        session: Optional[AsyncSession] = None,
        user_id: Optional[int] = None,
        save_history: bool = True
    ) -> Optional[str]:
        """
        Генерация текста через OpenRouter API с поддержкой истории.

        Args:
            model: ID модели (например, "openai/gpt-4o")
            messages: Текущее сообщение пользователя в формате [{"role": "user", "content": "..."}]
            session: SQLAlchemy сессия (обязательна для работы с историей)
            user_id: ID пользователя (обязателен для работы с историей)
            save_history: Сохранять ли историю (по умолчанию True)

        Returns:
            Ответ от модели или None при ошибке
        """
        # Загружаем историю, если предоставлены session и user_id
        history = []
        if session and user_id:
            history = await self._load_history(session, user_id, model)

        # Объединяем историю с текущим сообщением
        full_messages = history + messages

        # Фильтруем сообщения с пустым content (поддержка multimodal — content может быть list)
        def _has_content(m):
            c = m.get("content")
            if isinstance(c, list):
                return bool(c)
            return bool(c and c.strip())
        full_messages = [m for m in full_messages if _has_content(m)]

        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.WEBHOOK_URL or "https://t.me/NexusAIBot",
            "X-Title": "NexusAI",
        }

        payload = {
            "model": model,
            "messages": full_messages,
            "temperature": 0.7,
            "max_tokens": 4000
        }

        # Если модель "думающая" (o1, r1, reasoning) — добавляем флаг
        if any(x in model for x in ["reasoning", "r1", "o1", "o3"]):
            payload["include_reasoning"] = True

        # Если модель Perplexity с поиском — добавляем флаги
        if "perplexity" in model.lower() and ("search" in model.lower() or "sonar" in model.lower()):
            payload["extra_body"] = {
                "use_context": True,
                "search_depth": "high" if "pro" in model.lower() else "standard"
            }

        # Логирование для отладки
        logger.info(f"Text Gen: model={model}, messages_count={len(full_messages)}")
        logger.debug(f"Text Gen payload: {payload}")

        try:
            async with aiohttp.ClientSession() as session_http:
                async with session_http.post(self.url, headers=headers, json=payload) as resp:
                    resp_text = await resp.text()

                    if resp.status != 200:
                        logger.error(f"Text Gen Error {resp.status}: {resp_text}")
                        return f"Error: API {resp.status}"

                    result = await resp.json()

                    if "choices" in result and len(result["choices"]) > 0:
                        assistant_content = result["choices"][0]["message"]["content"]

                        # Сохраняем в историю, если нужно
                        if save_history and session and user_id and messages:
                            user_message = messages[0].get("content", "") if messages else ""
                            if user_message and assistant_content:
                                await self._save_history(
                                    session, user_id, model, user_message, assistant_content
                                )

                        return assistant_content
                    else:
                        logger.error("Empty response from API")
                        return "Пустой ответ от нейросети."

        except Exception as e:
            logger.exception(f"Text Gen Exception: {e}")
            return None

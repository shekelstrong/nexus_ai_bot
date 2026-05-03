import aiohttp
import base64
import re
from typing import Optional, Union, List
from aiogram.types import BufferedInputFile

from config import settings
from utils.logger import logger

class StandardImageGenerator:
    """
    Генератор для стандартных image-моделей через OpenRouter (Gemini, DALL-E, и др.),
    кроме Seedream (у него свой класс).
    Поддерживает текстовый промпт и до 3 референсов.
    """
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        model: str,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        size: Optional[str] = None
    ) -> Optional[Union[str, BufferedInputFile]]:
        if reference_images is None:
            reference_images = []

        # GPT Image 2 via OpenRouter (openai/gpt-5.4-image-2)
        if "gpt-5.4-image-2" in model.lower() or "gpt-image-2" in model.lower():
            return await self._generate_gpt_image_2(prompt, reference_images, size=size)

        # --- ОПРЕДЕЛЯЕМ НУЖНЫЕ MODALITIES ---
        req_modalities = ["image"]

        # Только для Google/Gemini просим еще и текст
        if "gemini" in model.lower() or "google" in model.lower():
            req_modalities = ["image", "text"]

        # --- ЗАЩИТА ОТ ПУСТОГО ПРОМПТА ---
        # Если юзер прислал фото без подписи, даем базовую команду, чтобы OpenRouter не выдал ошибку 400
        safe_prompt = prompt.strip() if prompt and prompt.strip() else "Пожалуйста, используй эти изображения как референс и сгенерируй новое на их основе."

        # Формируем контент сообщения с учетом референсов
        content_parts = []
        
        # Добавляем референсы (изображения)
        for img_url in reference_images[:3]:  # Максимум 3
            # OpenRouter принимает и URL, и Base64 в одинаковом формате
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": img_url}
            })
        
        # Добавляем текстовый промпт (используем safe_prompt вместо prompt)
        content_parts.append({
            "type": "text",
            "text": safe_prompt
        })

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content_parts}],
            "modalities": req_modalities
        }

        try:
            timeout = aiohttp.ClientTimeout(total=300, sock_connect=60, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.url, headers=self.headers, json=payload) as resp:

                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"OpenRouter Image Error {resp.status}: {error_text}")
                        try:
                            err_json = await resp.json()
                            if "error" in err_json and "message" in err_json["error"]:
                                return f"Ошибка провайдера: {err_json['error']['message']}"
                        except:
                            pass
                        return f"Ошибка API ({resp.status})"

                    data = await resp.json()

                    if not data.get("choices") or len(data["choices"]) == 0:
                        return None

                    message = data["choices"][0]["message"]

                    # --- ВАРИАНТ 1: Картинка в поле 'images' (Стандарт OpenRouter) ---
                    if message.get("images"):
                        img_data = message["images"][0]

                        if isinstance(img_data, dict) and "image_url" in img_data:
                            url = img_data["image_url"].get("url")
                            return self._process_url(url)

                        if isinstance(img_data, str):
                            return self._process_url(img_data)

                    # --- ВАРИАНТ 2: Картинка в 'content' (Стиль OpenAI/Gemini) ---
                    content = message.get("content")

                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "image_url":
                                url_obj = part.get("image_url")
                                if isinstance(url_obj, dict):
                                    url = url_obj.get("url")
                                    return self._process_url(url)

                    if isinstance(content, str):
                        # Проверяем, не является ли это сообщением об ошибке
                        content_lower = content.lower()
                        if "error" in content_lower or "credit" in content_lower or "payment" in content_lower:
                            logger.warning(f"Image gen: Response contains error message: {content[:200]}")
                            return f"Ошибка генерации: {content[:200]}"
                        
                        # Ищем URL картинки в формате Markdown: ![text](url)
                        url_match = re.search(r'!\[.*?\]\((https?://[^\)]+)\)', content)
                        if url_match:
                            return url_match.group(1)
                        
                        # Ищем URL в формате [text](url)
                        url_match = re.search(r'\[.*?\]\((https?://[^\)]+)\)', content)
                        if url_match:
                            url = url_match.group(1)
                            if 'openrouter.ai' not in url and 'settings' not in url:
                                return url
                        
                        # Ищем простой URL
                        url_simple = re.search(r'(https?://[^\s\]>"]+)', content)
                        if url_simple:
                            url = url_simple.group(1)
                            if 'openrouter.ai' not in url and 'settings' not in url:
                                return url

                        # Если контент короткий и не содержит ошибок - возвращаем как текст
                        if len(content) < 1000 and "error" not in content_lower:
                            return content

                    logger.warning(f"Image gen: No image found in response.")
                    return None

        except Exception as e:
            logger.error(f"StandardImageGenerator Error: {e}")
            return f"System Error: {str(e)}"

    async def _generate_gpt_image_2(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        size: Optional[str] = None
    ) -> Optional[Union[str, BufferedInputFile]]:
        """Generate image via OpenAI Images API (gpt-image-1 / dall-e-3)."""
        from config import settings as cfg
        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {cfg.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        # openai/gpt-5.4-image-2 идёт через OpenRouter как multimodal модель
        safe_prompt = (prompt or "").strip() or "A beautiful creative image"
        try:
            timeout = aiohttp.ClientTimeout(total=300, sock_connect=60)
            chat_url = "https://openrouter.ai/api/v1/chat/completions"

            content_parts = []
            for img_url in (reference_images or [])[:3]:
                content_parts.append({"type": "image_url", "image_url": {"url": img_url}})
            content_parts.append({"type": "text", "text": safe_prompt})

            chat_payload = {
                "model": "openai/gpt-5.4-image-2",
                "messages": [{"role": "user", "content": content_parts}],
                "modalities": ["image", "text"]
            }

            # Добавляем размер, если указан
            if size:
                chat_payload["image_config"] = {"size": size}
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(chat_url, headers=self.headers, json=chat_payload) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        logger.error(f"GPT Image 2 Error {resp.status}: {err}")
                        return f"Error {resp.status}"
                    data = await resp.json()
                    msg = data.get("choices", [{}])[0].get("message", {})
                    images = msg.get("images", [])
                    if images:
                        raw = images[0]
                        url = raw if isinstance(raw, str) else raw.get("image_url", {}).get("url")
                        return self._process_url(url)
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "image_url":
                                return self._process_url(part["image_url"].get("url"))
                    return None
        except Exception as e:
            logger.error(f"GPT Image 2 Exception: {e}")
            return None

    def _process_url(self, url: str) -> Union[str, BufferedInputFile, None]:
        """Обрабатывает URL или Base64 строку"""
        if not url:
            return None

        if url.startswith("data:image"):
            try:
                base64_str = url.split(",", 1)[1]
                return BufferedInputFile(base64.b64decode(base64_str), filename="generated.png")
            except Exception as e:
                logger.error(f"Base64 decode error: {e}")
                return None

        return url
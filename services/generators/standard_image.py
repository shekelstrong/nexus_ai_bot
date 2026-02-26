import aiohttp
import base64
import re
from typing import Optional, Union
from aiogram.types import BufferedInputFile

from config import settings
from utils.logger import logger

class StandardImageGenerator:
    """
    Генератор для стандартных image-моделей через OpenRouter (Gemini, DALL-E, и др.),
    кроме Seedream (у него свой класс).
    """
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Для картинок Referer часто не нужен или даже мешает, оставляем пустым
        }

    async def generate(self, model: str, prompt: str) -> Optional[Union[str, BufferedInputFile]]:
        
        # --- ОПРЕДЕЛЯЕМ НУЖНЫЕ MODALITIES ---
        # По умолчанию просим только картинку
        req_modalities = ["image"]
        
        # Только для Google/Gemini просим еще и текст (так как они болтливые и могут вернуть отказ текстом)
        if "gemini" in model.lower() or "google" in model.lower():
            req_modalities = ["image", "text"]
            
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": req_modalities
        }

        try:
            # Timeout: total=300 (5 min), sock_read=120 (2 min)
            timeout = aiohttp.ClientTimeout(total=300, sock_connect=60, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.url, headers=self.headers, json=payload) as resp:
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"OpenRouter Image Error {resp.status}: {error_text}")
                        # Пытаемся вернуть красивую ошибку, если она есть в JSON
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
                        
                        # Если это словарь с URL
                        if isinstance(img_data, dict) and "image_url" in img_data:
                            url = img_data["image_url"].get("url")
                            return self._process_url(url)
                            
                        # Если это просто строка (URL или base64)
                        if isinstance(img_data, str):
                            return self._process_url(img_data)

                    # --- ВАРИАНТ 2: Картинка в 'content' (Стиль OpenAI/Gemini) ---
                    content = message.get("content")
                    
                    # 2.1 Content как список объектов
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "image_url":
                                url_obj = part.get("image_url")
                                if isinstance(url_obj, dict):
                                    url = url_obj.get("url")
                                    return self._process_url(url)
                    
                    # 2.2 Content как строка (Markdown или текст ошибки)
                    if isinstance(content, str):
                        # Ищем Markdown image: ![alt](url) или просто (url)
                        url_match = re.search(r'\((https?://[^\)]+)\)', content)
                        if url_match:
                            return url_match.group(1)
                        
                        # Ищем просто ссылку в тексте
                        url_simple = re.search(r'(https?://\S+)', content)
                        if url_simple:
                            return url_simple.group(1)
                        
                        # Если ссылок нет — значит вернулся текст ошибки (например "I cannot generate...")
                        # Возвращаем этот текст, чтобы бот показал его юзеру
                        if len(content) < 1000:
                            return content

                    logger.warning(f"Image gen: No image found in response. Keys: {message.keys()}")
                    return None

        except Exception as e:
            logger.error(f"StandardImageGenerator Error: {e}")
            return f"System Error: {str(e)}"

    def _process_url(self, url: str) -> Union[str, BufferedInputFile]:
        """Обрабатывает URL или Base64 строку"""
        if not url:
            return None
            
        if url.startswith("data:image"):
            try:
                # data:image/png;base64,.....
                base64_str = url.split(",", 1)[1]
                return BufferedInputFile(base64.b64decode(base64_str), filename="generated.png")
            except Exception as e:
                logger.error(f"Base64 decode error: {e}")
                return None
                
        return url
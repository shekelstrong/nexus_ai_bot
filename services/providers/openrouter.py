import aiohttp
import base64
from typing import Optional, List, Dict, Union
from aiogram.types import BufferedInputFile

from config import settings
from utils.logger import logger
from .base import BaseProvider

class OpenRouterProvider(BaseProvider):
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.chat_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nexusai.bot",
            "X-Title": "Nexus AI Bot",
        }

    async def generate_text(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4000)
        }
        
        # Специфичные флаги для рассуждающих моделей
        if any(x in model for x in ["reasoning", "r1", "o1", "o3"]):
             payload["include_reasoning"] = True

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chat_url, headers=self.headers, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"OpenRouter Text Error {resp.status}: {error_text}")
                        return f"Error: API {resp.status}"
                    
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter Text Exception: {e}")
            return None

    async def generate_image(self, model: str, prompt: str, **kwargs) -> Optional[Union[str, BufferedInputFile]]:
        # Для картинок убираем лишние заголовки, чтобы мимикрировать под чистый API запрос
        img_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # ЛОГИКА MODALITIES:
        # Seedream падает, если просить text + image. Ему нужно только image.
        req_modalities = ["image", "text"]
        if "seedream" in model.lower():
            req_modalities = ["image"]

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": req_modalities
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chat_url, headers=img_headers, json=payload) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        logger.error(f"OpenRouter Image Error {resp.status}: {err_text}")
                        return None
                    
                    data = await resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        message = data["choices"][0]["message"]
                        
                        # Если картинка пришла в поле images
                        if "images" in message and message["images"]:
                            img_data = message["images"][0]
                            
                            # Вариант 1: Объект с url (возможно base64)
                            if isinstance(img_data, dict) and "image_url" in img_data:
                                img_url = img_data["image_url"]["url"]
                                if img_url.startswith("data:image"):
                                    # Декодируем base64
                                    base64_str = img_url.split(",", 1)[1]
                                    return BufferedInputFile(base64.b64decode(base64_str), filename="generated.png")
                                return img_url
                            
                            # Вариант 2: Просто строка URL
                            if isinstance(img_data, str):
                                return img_data
        except Exception as e:
            logger.error(f"OpenRouter Image Exception: {e}")
            return None
        
        return None
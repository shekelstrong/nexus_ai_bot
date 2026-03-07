# services/generators/seedream.py
import aiohttp
import base64
from typing import Optional, Union, List
from aiogram.types import BufferedInputFile
from config import settings
from utils.logger import logger

class SeedreamGenerator:
    """
    Генератор для Seedream (ByteDance) через OpenRouter.
    Поддерживает текстовый промпт и до 3 референсов.
    """
    def __init__(self):
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.key = settings.OPENROUTER_API_KEY

    async def generate(
        self,
        model: str,
        prompt: str,
        reference_images: Optional[List[str]] = None
    ) -> Optional[Union[str, BufferedInputFile]]:
        if reference_images is None:
            reference_images = []
        
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

        # Формируем контент с референсами
        content_parts = []
        
        # Добавляем референсы (изображения) - максимум 3
        for img_url in reference_images[:3]:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": img_url}
            })
        
        # Добавляем текстовый промпт
        content_parts.append({
            "type": "text",
            "text": prompt
        })

        # Seedream требует только image в modalities
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content_parts}],
            "modalities": ["image"]
        }

        try:
            timeout = aiohttp.ClientTimeout(total=300, sock_connect=60, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Seedream Error {resp.status}: {await resp.text()}")
                        return None

                    data = await resp.json()
                    message = data["choices"][0]["message"]

                    if "images" in message and message["images"]:
                        img_data = message["images"][0]
                        if isinstance(img_data, dict) and "image_url" in img_data:
                            img_url = img_data["image_url"]["url"]
                            if img_url.startswith("data:image"):
                                base64_str = img_url.split(",", 1)[1]
                                return BufferedInputFile(base64.b64decode(base64_str), filename="seedream_gen.png")
                            return img_url
                        return img_data
        except Exception as e:
            logger.error(f"Seedream Exception: {e}")
            return None
        return None
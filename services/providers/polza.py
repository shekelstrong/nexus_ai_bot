"""Polza.AI Provider — заменяет services/providers/fal.py"""
from typing import Optional, List, Dict, Union
from aiogram.types import BufferedInputFile

from config import settings
from utils.logger import logger
from .base import BaseProvider


class PolzaProvider(BaseProvider):
    """Провайдер для Polza.AI — изображения, видео через Polza AI."""

    def __init__(self):
        self.api_key = settings.POLZA_AI_API_KEY
        self.base_url = "https://polza.ai/api"
        self.chat_url = f"{self.base_url}/v1/chat/completions"
        self.image_url = f"{self.base_url}/v2/images/generations"
        self.media_url = f"{self.base_url}/v1/media"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate_text(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Генерация текста через Polza.AI Chat Completions."""
        import aiohttp
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4000),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chat_url, headers=self.headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Polza Text Error {resp.status}: {await resp.text()[:200]}")
                        return None
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Polza Text Exception: {e}")
            return None

    async def generate_image(self, model: str, prompt: str, **kwargs) -> Optional[Union[str, BufferedInputFile]]:
        """Генерация изображения через Polza.AI Images API."""
        import aiohttp
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "response_format": "url",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.image_url, headers=self.headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Polza Image Error {resp.status}: {await resp.text()[:200]}")
                        return None
                    data = await resp.json()
                    if data.get("data") and len(data["data"]) > 0:
                        return data["data"][0].get("url")
        except Exception as e:
            logger.error(f"Polza Image Exception: {e}")
            return None
        return None

    async def generate_video(self, model: str, prompt: str, **kwargs) -> Optional[str]:
        """Генерация видео через Polza.AI Media API."""
        import aiohttp
        import asyncio

        payload = {
            "model": model,
            "input": {"prompt": prompt},
            "async": True,
        }
        
        if "aspect_ratio" in kwargs:
            payload["input"]["aspect_ratio"] = kwargs["aspect_ratio"]
        if "image_url" in kwargs:
            payload["input"]["images"] = [{"type": "url", "data": kwargs["image_url"]}]

        try:
            async with aiohttp.ClientSession() as session:
                # Submit
                async with session.post(self.media_url, headers=self.headers, json=payload) as resp:
                    if resp.status not in (200, 201):
                        logger.error(f"Polza Video Error {resp.status}: {await resp.text()[:200]}")
                        return None
                    result = await resp.json()

                # Check for immediate result
                url = result.get("url") or result.get("video_url")
                if url:
                    return url

                media_id = result.get("id") or result.get("media_id")
                if not media_id:
                    return None

                # Poll
                status_url = f"{self.base_url}/v1/media/{media_id}/status"
                for _ in range(60):
                    await asyncio.sleep(5)
                    async with session.get(status_url, headers=self.headers) as s_resp:
                        if s_resp.status != 200:
                            continue
                        s_data = await s_resp.json()
                        status = s_data.get("status", "").upper()
                        if status == "COMPLETED":
                            for k in ["url", "video_url"]:
                                if s_data.get(k):
                                    return s_data[k]
                            # Check response_url
                            resp_url = s_data.get("response_url")
                            if resp_url:
                                async with session.get(resp_url, headers=self.headers) as f_resp:
                                    if f_resp.status == 200:
                                        f_data = await f_resp.json()
                                        for k in ["url", "video_url"]:
                                            if f_data.get(k):
                                                return f_data[k]
                            return None
                        if status == "FAILED":
                            return None
        except Exception as e:
            logger.error(f"Polza Video Exception: {e}")
            return None
        return None

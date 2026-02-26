import aiohttp
import asyncio
from typing import Optional, Union, List, Dict
from aiogram.types import BufferedInputFile

from config import settings
from utils.logger import logger
from .base import BaseProvider

class FalProvider(BaseProvider):
    def __init__(self):
        self.api_key = settings.FAL_AI_API_KEY
        self.base_url = "https://fal.run/"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_text(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        # FAL обычно не используется для текста в этом боте, но заглушку оставить нужно
        return None

    async def generate_image(self, model: str, prompt: str, **kwargs) -> Optional[Union[str, BufferedInputFile]]:
        endpoint = "fal-ai/flux/schnell" # Дефолт
        
        # Подбор эндпоинта
        if "flux.2-pro" in model: endpoint = "fal-ai/flux-pro/v1.1"
        elif "flux.2-max" in model: endpoint = "fal-ai/flux/dev"
        elif "flux.2-flex" in model: endpoint = "fal-ai/flux/dev" # или flex если есть
        elif "stable-diffusion" in model: endpoint = "fal-ai/fast-sdxl"
        
        payload = {
            "prompt": prompt,
            "image_size": "landscape_4_3",
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": False,
            "sync_mode": True # Ждем ответ сразу
        }
        
        # Оптимизация для Schnell
        if "schnell" in endpoint:
             payload.update({"num_inference_steps": 4})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url + endpoint, headers=self.headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"FalAI Image Error {resp.status}: {await resp.text()}")
                        return None
                    
                    data = await resp.json()
                    if data.get("images"):
                        return data["images"][0]["url"]
        except Exception as e:
            logger.error(f"FalAI Image Ex: {e}")
            return None
        return None

    async def generate_video(self, model: str, prompt: str, **kwargs) -> Optional[str]:
        # Видео модели: Kling, Luma, Hailuo, Veo
        endpoint = "fal-ai/kling-video/v1/standard/text-to-video" # Дефолт Kling
        
        if "luma" in model: endpoint = "fal-ai/luma-dream-machine"
        elif "hailuo" in model: endpoint = "fal-ai/minimax-video"
        elif "veo" in model: endpoint = "fal-ai/veo/v3" # Примерный эндпоинт, уточнить в доке FAL если выйдет

        payload = {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "duration": "5" # Обычно 5 сек для старта
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Отправляем задачу
                async with session.post(self.base_url + endpoint, headers=self.headers, json=payload) as resp:
                    if resp.status not in (200, 201):
                        logger.error(f"FalAI Video Start Error {resp.status}: {await resp.text()}")
                        return None
                    
                    data = await resp.json()
                    
                    # Если ответ синхронный (иногда бывает)
                    if "video" in data: return data["video"]["url"]
                    if "video_url" in data: return data["video_url"]
                    
                    # Если асинхронный - берем request_id
                    request_id = data.get("request_id")
                    if not request_id:
                        return None

                # 2. Поллинг (ждем готовности)
                for _ in range(60): # Ждем макс 60 * 2 = 120 сек
                    await asyncio.sleep(2)
                    status_url = f"https://fal.run/requests/{request_id}/status" # Или другой URL для проверки статуса API FAL
                    # Примечание: FAL часто возвращает статус по тому же URL запроса но GET, или через спец. эндпоинт queue.
                    # Но чаще всего в библиотеках используют requests/{id}
                    
                    # Упростим: для видео часто используется endpoint + /requests/id или просто ждем вебхук.
                    # В простом варианте FAL возвращает response_url для проверки.
                    # Если data имеет response_url, используем его
                    
                    check_url = data.get("response_url")
                    if not check_url:
                        # Если нет response_url, пробуем стандартный паттерн FAL (queue)
                        # Но для простоты: многие эндпоинты FAL сейчас поддерживают sync_mode=True и для видео, но это долго.
                        # Лучше проверить response_url
                        return None

                    async with session.get(check_url, headers=self.headers) as check_resp:
                        if check_resp.status == 200:
                            res_data = await check_resp.json()
                            status = res_data.get("status") # IN_QUEUE, IN_PROGRESS, COMPLETED
                            
                            if status == "COMPLETED":
                                if "video" in res_data: return res_data["video"]["url"]
                                if "video_url" in res_data: return res_data["video_url"]
                                if "images" in res_data: return res_data["images"][0]["url"] # Иногда видео приходит как массив
                            
                            if status == "FAILED":
                                logger.error(f"FalAI Video Failed: {res_data}")
                                return None
        except Exception as e:
            logger.error(f"FalAI Video Ex: {e}")
            return None
            
        return None
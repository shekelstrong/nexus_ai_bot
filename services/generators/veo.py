import aiohttp
import asyncio
from typing import Optional, Dict
from config import settings
from utils.logger import logger

class VeoGenerator:
    def __init__(self):
        self.api_key = settings.FAL_AI_API_KEY
        self.base_url = "https://queue.fal.run"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate(self, model_id: str, prompt: str, image_url: Optional[str] = None, extra_params: Optional[Dict] = None) -> Optional[str]:
        """
        Генерация для Google Veo 3.1
        """
        # Veo требует описание движения. Если юзер скинул только фото, ставим дефолтное
        safe_prompt = prompt if prompt and prompt.strip() else "Smoothly and naturally animate the transition between the first and last frame, keeping high realism."
        payload = {"prompt": safe_prompt}

        # Режимы
        if "first-last" in model_id:
            # ИСПРАВЛЕНИЕ: Fal AI по факту требует first_frame_image_url и last_frame_image_url
            if not image_url: return None
            payload["first_frame_image_url"] = image_url
            
            end_url = extra_params.get("second_image_url") if extra_params else None
            if not end_url:
                logger.warning("Veo First-Last: No second image")
                return None
            payload["last_frame_image_url"] = end_url

        elif "image-to-video" in model_id or "reference-to-video" in model_id:
            if not image_url: return None
            payload["image_url"] = image_url

        else:
            # Text to Video
            payload["aspect_ratio"] = "16:9"

        return await self._submit_and_poll(model_id, payload)

    async def _submit_and_poll(self, model_id: str, payload: Dict) -> Optional[str]:
        try:
            timeout = aiohttp.ClientTimeout(total=600, sock_connect=120, sock_read=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                submit_url = f"{self.base_url}/{model_id}"
                async with session.post(submit_url, headers=self.headers, json=payload) as resp:
                    if resp.status not in [200, 201]:
                        logger.error(f"Veo Error {resp.status}: {await resp.text()}")
                        return None
                    data = await resp.json()
                    
                # На случай быстрого ответа
                if "video" in data:
                    return data["video"].get("url")
                if "video_url" in data:
                    return data["video_url"]

                request_id = data.get("request_id")
                if not request_id: 
                    logger.error(f"Veo no request_id. Data: {data}")
                    return None
                
                # ВАЖНО: Используем правильный endpoint для поллинга статуса
                status_url = data.get("status_url") or f"{self.base_url}/{model_id}/requests/{request_id}/status"
                
                for _ in range(120): # Ожидание до 10 минут
                    await asyncio.sleep(5)
                    try:
                        async with session.get(status_url, headers=self.headers) as resp:
                            if resp.status != 200: continue
                            data = await resp.json()
                            status = data.get("status")
                            
                            if status == "COMPLETED":
                                res = data.get("response", data)
                                return res.get("video", {}).get("url") or res.get("video_url")
                            elif status == "FAILED":
                                logger.error(f"Veo Task Failed: {data.get('error')}")
                                return None
                    except Exception as poll_e:
                        # Игнорируем временные сбои сети при поллинге
                        logger.warning(f"Veo Poll exception (ignoring): {poll_e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Veo Exception: {e}")
            return None
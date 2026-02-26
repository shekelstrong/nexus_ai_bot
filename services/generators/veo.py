import aiohttp
import asyncio
from typing import Optional, Dict
from config import settings
from utils.logger import logger

class VeoGenerator:
    def __init__(self):
        self.api_key = settings.FAL_AI_API_KEY
        self.base_url = "https://fal.run"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate(self, model_id: str, prompt: str, image_url: Optional[str] = None, extra_params: Optional[Dict] = None) -> Optional[str]:
        """
        Генерация для Google Veo 3.1
        """
        payload = {"prompt": prompt}
        
        # Режимы
        if "first-last" in model_id:
            # Требует image_url (start) и end_image_url (end)
            if not image_url: return None
            payload["image_url"] = image_url
            
            end_url = extra_params.get("second_image_url")
            if not end_url:
                logger.warning("Veo First-Last: No second image")
                return None
            payload["end_image_url"] = end_url # В некоторых версиях FAL это 'tail_image_url' или массив. Проверим доку: для veo3.1/fast/first-last это 'end_image_url'.
            
        elif "image-to-video" in model_id:
            if not image_url: return None
            payload["image_url"] = image_url
            
        else:
            # Text to Video
            payload["aspect_ratio"] = "16:9"

        return await self._submit_and_poll(model_id, payload)

    async def _submit_and_poll(self, model_id: str, payload: Dict) -> Optional[str]:
        try:
            # Таймауты для работы с большими файлами
            timeout = aiohttp.ClientTimeout(total=600, sock_connect=120, sock_read=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/{model_id}"
                async with session.post(url, headers=self.headers, json=payload) as resp:
                    if resp.status not in [200, 201]:
                        logger.error(f"Veo Error {resp.status}: {await resp.text()}")
                        return None
                    data = await resp.json()
                    
                request_id = data.get("request_id")
                if not request_id: return None
                
                status_url = f"{self.base_url}/{model_id}/requests/{request_id}"
                for _ in range(60):
                    await asyncio.sleep(5)
                    async with session.get(status_url, headers=self.headers) as resp:
                        if resp.status != 200: continue
                        data = await resp.json()
                        if data.get("status") == "COMPLETED":
                            res = data.get("response", data)
                            return res.get("video", {}).get("url") or res.get("video_url")
                        if data.get("status") == "FAILED":
                            return None
        except Exception as e:
            logger.error(f"Veo Exception: {e}")
            return None

import asyncio
from typing import Optional, Dict, Any

import aiohttp

from config import settings
from utils.logger import logger


class KlingGenerator:
    """
    Генератор Kling через fal.ai Queue API.
    Использует очередь (Queue) для долгих задач.
    """

    def __init__(self):
        self.api_key = settings.FAL_AI_API_KEY
        self.base_url = "https://queue.fal.run"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        model_id: str,
        prompt: str,
        image_url: Optional[str] = None,
        extra_params: Optional[Dict] = None,
    ) -> Optional[str]:
        if extra_params is None:
            extra_params = {}

        payload = self._build_payload(model_id, prompt, image_url, extra_params)
        if not payload:
            logger.error(f"Kling: не удалось сформировать payload для {model_id}")
            return None

        submit_url = f"{self.base_url}/{model_id}"
        logger.info(f"Kling Queue Submit: {submit_url}")

        timeout = aiohttp.ClientTimeout(total=60)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(submit_url, headers=self.headers, json=payload) as resp:
                    if resp.status not in (200, 201):
                        err_text = await resp.text()
                        logger.error(f"Kling Queue Submit Error {resp.status}: {err_text}")
                        return None
                    data = await resp.json()
                
                # ЛОГИРУЕМ ОТВЕТ СЕРВЕРА ЦЕЛИКОМ (для отладки)
                logger.info(f"Kling Submit Response: {data}")

                quick_url = self._extract_media_url(data)
                if quick_url:
                    logger.info("Kling: получен быстрый результат")
                    return quick_url

                request_id = data.get("request_id")
                
                # FAL возвращает разные URL для проверки
                # status_url - для проверки статуса (json)
                # response_url - для получения результата (иногда совпадает)
                status_url = data.get("status_url") 
                if not status_url:
                     # Если явного status_url нет, берем response_url
                     status_url = data.get("response_url")

                if not request_id:
                    logger.error(f"Kling: нет request_id. Ответ: {data}")
                    return None

                return await self._poll_result(
                    session=session,
                    model_id=model_id,
                    request_id=request_id,
                    status_url=status_url,
                    poll_seconds=10,
                    max_wait_seconds=1200 
                )

        except Exception as e:
            logger.error(f"Kling Exception: {e}")
            return None

    def _build_payload(
        self,
        model_id: str,
        prompt: str,
        image_url: Optional[str],
        extra_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        model_lower = (model_id or "").lower()

        # Motion Control
        if "motion-control" in model_lower:
            if not image_url: return None
            video_url = extra_params.get("video_url")
            if not video_url: return None

            payload = {
                "prompt": prompt or "A person performing an action from the reference video",
                "image_url": image_url,
                "video_url": video_url,
                "keep_original_sound": extra_params.get("keep_original_sound", True),
                "character_orientation": extra_params.get("character_orientation", "video"),
            }
            logger.info("Kling: режим Motion Control обнаружен.")
            return payload

        # Image-to-Video
        if "image-to" in model_lower or "img2vid" in model_lower:
            if not image_url: return None
            return {
                "prompt": prompt or "High quality video",
                "image_url": image_url,
                "duration": "5",
                "aspect_ratio": "16:9",
                "cfg_scale": 0.5
            }

        # Text-to-Video
        payload = {
            "prompt": prompt or "Masterpiece",
            "duration": "5",
            "aspect_ratio": "16:9",
            "cfg_scale": 0.5
        }
        if image_url: payload["image_url"] = image_url
        return payload

    def _extract_media_url(self, data: Any) -> Optional[str]:
        if not isinstance(data, dict): return None
        if "video" in data and isinstance(data["video"], dict): return data["video"].get("url")
        if "video_url" in data and isinstance(data["video_url"], str): return data["video_url"]
        if "images" in data and isinstance(data["images"], list) and data["images"]:
            return data["images"][0].get("url")
        if "url" in data and isinstance(data["url"], str): return data["url"]
        return None

    async def _poll_result(
        self,
        session: aiohttp.ClientSession,
        model_id: str,
        request_id: str,
        status_url: Optional[str] = None,
        poll_seconds: int = 10,
        max_wait_seconds: int = 1200,
    ) -> Optional[str]:
        
        # Если URL так и не дали, собираем вручную по доке
        if not status_url:
            status_url = f"{self.base_url}/{model_id}/requests/{request_id}/status"

        logger.info(f"Kling Poll: Start polling request_id={request_id}")
        logger.info(f"Kling Poll: URL={status_url}")
        
        start_time = asyncio.get_running_loop().time()

        while True:
            elapsed = asyncio.get_running_loop().time() - start_time
            if elapsed > max_wait_seconds:
                logger.error(f"Kling Poll: Timeout ({max_wait_seconds}s)")
                return None

            await asyncio.sleep(poll_seconds)

            try:
                async with session.get(status_url, headers=self.headers) as resp:
                    if resp.status != 200:
                        # ВАЖНО: читаем текст ошибки
                        err_text = await resp.text() 
                        logger.warning(f"Kling Poll: status check failed {resp.status}. Body: {err_text}")
                        # Если 400 или 404 - возможно, мы долбимся не туда, или задача исчезла
                        if resp.status in [400, 404]:
                             # Попробуем альтернативный URL (без /status на конце)
                             alt_url = f"{self.base_url}/{model_id}/requests/{request_id}"
                             if status_url != alt_url:
                                 logger.info(f"Kling Poll: Trying alt URL: {alt_url}")
                                 status_url = alt_url
                                 continue
                             else:
                                 return None # Всё, приехали
                        continue
                    
                    data = await resp.json()
            except Exception as e:
                logger.error(f"Kling Poll: Error: {e}")
                continue

            status = data.get("status")

            if status == "COMPLETED":
                result_url = self._extract_media_url(data)
                if result_url:
                    logger.info(f"Kling Poll: COMPLETED. URL: {result_url}")
                    return result_url
                
                # Если в статусе нет ссылки, пробуем response_url
                response_url = data.get("response_url")
                if response_url:
                     try:
                        async with session.get(response_url, headers=self.headers) as final_resp:
                            if final_resp.status == 200:
                                final_data = await final_resp.json()
                                result_url = self._extract_media_url(final_data)
                                if result_url: return result_url
                     except: pass
                
                logger.error(f"Kling Poll: COMPLETED, но ссылка не найдена. Data: {data}")
                return None

            elif status == "FAILED":
                logger.error(f"Kling Poll: FAILED. Reason: {data.get('error')}")
                return None
            
            elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                if int(elapsed) % 30 < poll_seconds:
                     logger.info(f"Kling Poll: {status} ({int(elapsed)}s)")
                continue
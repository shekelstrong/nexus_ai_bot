import asyncio
import aiohttp
import base64
from typing import Optional, Dict, Any

from config import settings
from utils.logger import logger


class FalVideoGenerator:
    def __init__(self):
        self.api_key = settings.FAL_AI_API_KEY

        # ВАЖНО:
        # Для долгих задач (Kling и т.п.) используем очередь, чтобы не держать один HTTP-запрос открытым.
        # Submit:  POST https://queue.fal.run/{model_id}
        # Status:  GET  https://queue.fal.run/{model_id}/requests/{request_id}
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
        """
        Универсальный метод генерации для FAL.AI через Queue API.
        Возвращает URL результата (video/images) или None.
        """
        if extra_params is None:
            extra_params = {}

        # Если передали байты видео в extra_params, конвертируем в data:uri
        # (работает только если видео не слишком большое для payload).
        if "video_data" in extra_params and isinstance(extra_params["video_data"], bytes):
            vid_bytes = extra_params["video_data"]
            b64_vid = base64.b64encode(vid_bytes).decode("utf-8")
            extra_params["video_url"] = f"data:video/mp4;base64,{b64_vid}"

        endpoint = self._get_endpoint(model_id)
        payload = self._build_payload(model_id, prompt, image_url, extra_params)

        if not payload:
            logger.error(f"FAL: Не удалось сформировать payload для {model_id}")
            return None

        logger.info(f"FAL Queue Submit: {endpoint} | Payload keys: {list(payload.keys())}")

        # Для queue submit/status запросы должны быть быстрыми: это небольшие JSON-ответы.
        timeout = aiohttp.ClientTimeout(total=60, sock_connect=20, sock_read=40)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                submit_url = f"{self.base_url}/{model_id}"

                async with session.post(submit_url, headers=self.headers, json=payload) as resp:
                    if resp.status not in (200, 201):
                        err_text = await resp.text()
                        logger.error(f"FAL Queue Submit Error {resp.status}: {err_text}")
                        return None

                    data = await resp.json()

                # Иногда API может вернуть быстрый результат сразу
                quick = self._extract_media_url(data)
                if quick:
                    return quick

                # Queue API обычно возвращает request_id + response_url
                request_id = data.get("request_id") or data.get("id")
                response_url = data.get("response_url")

                if not request_id:
                    logger.error(f"FAL: Submit ответ без request_id. Keys={list(data.keys())}")
                    return None

                return await self._poll_result(
                    session=session,
                    model_id=model_id,
                    request_id=request_id,
                    response_url=response_url,
                    poll_seconds=5,
                    max_wait_seconds=20 * 60,  # 20 минут
                )

        except Exception as e:
            logger.error(f"FAL Generator Error: {e}")
            return None

    def _get_endpoint(self, model_id: str) -> str:
        return model_id

    def _build_payload(
        self,
        model_id: str,
        prompt: str,
        image_url: Optional[str],
        extra_params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        params = extra_params or {}
        model = model_id.lower()

        payload: Dict[str, Any] = {"prompt": prompt}

        # --- KLING 2.6 ---
        if "kling" in model:
            # лучше отправлять duration числом (на всякий случай)
            payload["duration"] = 5
            payload["aspect_ratio"] = "16:9"
            payload["cfg_scale"] = 0.5

            # Motion Control (Img + Video)
            if "motion-control" in model:
                if not image_url:
                    return None
                payload["image_url"] = image_url

                vid_url = params.get("video_url")
                if not vid_url:
                    logger.warning("Kling Motion: No video_url")
                    return None
                payload["video_url"] = vid_url

                # Доп.поля, если передали
                if "character_orientation" in params:
                    payload["character_orientation"] = params["character_orientation"]
                if "keep_original_sound" in params:
                    payload["keep_original_sound"] = params["keep_original_sound"]

            # Image to Video (Img only)
            elif "image-to-video" in model:
                if not image_url:
                    return None
                payload["image_url"] = image_url

            # Text to Video (Prompt only) — payload уже содержит prompt

        # --- VEO 3.1 ---
        elif "veo3.1" in model:
            if "image-to-video" in model:
                if not image_url:
                    return None
                payload["image_url"] = image_url

            elif "first-last" in model:
                if not image_url:
                    return None
                payload["image_url"] = image_url  # start frame

                end_url = params.get("second_image_url")
                if not end_url:
                    return None
                payload["end_image_url"] = end_url  # end frame

            elif "text" in model:
                payload["aspect_ratio"] = "16:9"

        # --- WAN 2.6 ---
        elif "wan" in model:
            if "image-to-video" in model:
                if not image_url:
                    return None
                payload["image_url"] = image_url
            elif "text-to-video" in model:
                payload["aspect_ratio"] = "16:9"

        # --- STABLE DIFFUSION (FAL) ---
        elif "stable-diffusion" in model:
            payload = {
                "prompt": prompt,
                "image_size": "landscape_4_3",
                "num_inference_steps": 28,
                "enable_safety_checker": False,
                "sync_mode": True,
            }
            if image_url:
                payload["image_url"] = image_url

        # --- LUMA ---
        elif "luma" in model:
            payload = {"prompt": prompt, "aspect_ratio": "16:9"}

        return payload

    def _extract_media_url(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Пытаемся достать URL результата из разных возможных форматов ответа.
        """
        if not isinstance(data, dict):
            return None

        # Иногда результат лежит в data["response"]
        if "response" in data and isinstance(data["response"], dict):
            inner = self._extract_media_url(data["response"])
            if inner:
                return inner

        # Видео
        if "video" in data and isinstance(data["video"], dict) and "url" in data["video"]:
            return data["video"]["url"]
        if "video_url" in data and isinstance(data["video_url"], str):
            return data["video_url"]

        # Картинки
        if "images" in data and isinstance(data["images"], list) and len(data["images"]) > 0:
            first = data["images"][0]
            if isinstance(first, dict) and "url" in first:
                return first["url"]

        # Иногда бывает просто url
        if "url" in data and isinstance(data["url"], str):
            return data["url"]

        return None

    async def _poll_result(
        self,
        session: aiohttp.ClientSession,
        model_id: str,
        request_id: str,
        response_url: Optional[str] = None,
        poll_seconds: int = 5,
        max_wait_seconds: int = 20 * 60,
    ) -> Optional[str]:
        """
        Опрос статуса в очереди до COMPLETED/FAILED или таймаута ожидания.
        """
        status_url = response_url or f"{self.base_url}/{model_id}/requests/{request_id}"
        attempts = max(1, max_wait_seconds // poll_seconds)

        logger.info(f"FAL Queue Poll: request_id={request_id}, poll={poll_seconds}s, max_wait={max_wait_seconds}s")

        for i in range(attempts):
            await asyncio.sleep(poll_seconds)

            try:
                async with session.get(status_url, headers=self.headers) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
            except Exception:
                continue

            status = data.get("status")

            # Возможные статусы: IN_QUEUE / IN_PROGRESS / COMPLETED / FAILED
            if status == "COMPLETED":
                result = self._extract_media_url(data)
                if result:
                    return result

                # Если COMPLETED, но url не нашли — покажем ключи для диагностики
                logger.error(f"FAL: COMPLETED, но не найден media url. Keys={list(data.keys())}")
                return None

            if status == "FAILED":
                err = data.get("error")
                logger.error(f"FAL Task Failed: {err}")
                return None

            # Чтобы не спамить каждую итерацию
            if i in (0, 5, 20) or (i % 30 == 0):
                logger.info(f"FAL status={status} (attempt {i + 1}/{attempts})")

        logger.error("FAL: Таймаут ожидания результата из очереди")
        return None
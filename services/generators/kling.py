"""Kling генератор — переписан на Polza.AI Media API вместо Fal AI"""
from typing import Optional, Dict, Any

from services.polza_ai import generate_video, submit_media, poll_media, extract_media_url
from utils.logger import logger


class KlingGenerator:
    """Генерация Kling видео через Polza.AI Media API."""

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

        logger.info(f"Kling Polza Submit: model={model_id}")

        # Motion Control требует дополнительный video_url в images
        if "motion-control" in (model_id or "").lower():
            # Отправляем через polza_ai напрямую со специальными параметрами
            return await generate_video(
                model=model_id,
                prompt=prompt,
                image_url=image_url,
                extra_params=extra_params,
                poll_seconds=10,
                max_wait_seconds=1200,
            )

        # Стандартная медиа-генерация
        return await generate_video(
            model=model_id,
            prompt=payload.get("prompt", prompt),
            image_url=image_url,
            extra_params=payload,
            poll_seconds=10,
            max_wait_seconds=1200,
        )

    def _build_payload(
        self,
        model_id: str,
        prompt: str,
        image_url: Optional[str],
        extra_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        model_lower = (model_id or "").lower()

        aspect_ratio = extra_params.get("aspect_ratio", "16:9")
        duration = extra_params.get("duration", "5")

        # Image-to-Video
        if "image-to" in model_lower or "img2vid" in model_lower:
            if not image_url:
                return None
            return {
                "prompt": prompt or "High quality video",
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "cfg_scale": 0.5,
            }

        # Text-to-Video
        return {
            "prompt": prompt or "Masterpiece",
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "cfg_scale": 0.5,
        }

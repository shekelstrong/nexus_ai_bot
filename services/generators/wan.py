"""Wan 2.6 генератор — переписан на Polza.AI Media API вместо Fal AI"""
from typing import Optional, Dict

from services.polza_ai import generate_video
from utils.logger import logger


class WanGenerator:
    """Генерация Wan видео через Polza.AI Media API."""

    async def generate(
        self,
        model_id: str,
        prompt: str,
        image_url: Optional[str] = None,
        extra_params: Optional[Dict] = None,
    ) -> Optional[str]:
        if extra_params is None:
            extra_params = {}

        payload = {"aspect_ratio": "16:9"}

        if "image-to-video" in (model_id or ""):
            if not image_url:
                return None
        elif "reference" in (model_id or ""):
            if not image_url:
                return None

        return await generate_video(
            model=model_id,
            prompt=prompt,
            image_url=image_url,
            extra_params=payload,
            poll_seconds=5,
            max_wait_seconds=600,
        )

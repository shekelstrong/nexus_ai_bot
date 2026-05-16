"""Veo 3.1 генератор — переписан на Polza.AI Media API вместо Fal AI"""
from typing import Optional, Dict

from services.polza_ai import generate_video, extract_media_url, submit_media, poll_media
from utils.logger import logger


class VeoGenerator:
    """Генерация Google Veo через Polza.AI Media API."""

    async def generate(
        self,
        model_id: str,
        prompt: str,
        image_url: Optional[str] = None,
        extra_params: Optional[Dict] = None,
    ) -> Optional[str]:
        if extra_params is None:
            extra_params = {}

        safe_prompt = prompt if prompt and prompt.strip() else "Smoothly and naturally animate"
        payload = {"prompt": safe_prompt}

        if "first-last" in model_id:
            # First-Last-Frame: нужно 2 изображения
            if not image_url:
                return None
            end_url = extra_params.get("second_image_url")
            if not end_url:
                logger.warning("Veo First-Last: No second image")
                return None
            # Отправляем через generate_video с second_image_url в extra_params
            return await generate_video(
                model=model_id,
                prompt=safe_prompt,
                image_url=image_url,
                extra_params={"second_image_url": end_url},
                poll_seconds=10,
                max_wait_seconds=1800,
            )

        elif "image-to-video" in model_id or "reference-to-video" in model_id:
            if not image_url:
                return None
            return await generate_video(
                model=model_id,
                prompt=safe_prompt,
                image_url=image_url,
                poll_seconds=10,
                max_wait_seconds=1800,
            )

        else:
            # Image-to-Video если есть фото, иначе Text-to-Video
            aspect_ratio = extra_params.get("aspect_ratio", "16:9")
            return await generate_video(
                model=model_id,
                prompt=safe_prompt,
                image_url=image_url,
                extra_params={"aspect_ratio": aspect_ratio},
                poll_seconds=10,
                max_wait_seconds=1800,
            )

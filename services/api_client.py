import aiohttp
from typing import Optional, List, Dict, Union, Any
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from utils.logger import logger

from services.generators.standard_text import StandardTextGenerator
from services import openrouter
from services.polza_ai import (
    generate_media_image,
    generate_image as polza_generate_image,
    generate_video as polza_generate_video,
    generate_text as polza_generate_text,
)


class APIClient:
    def __init__(self):
        self.text_gen = StandardTextGenerator()

    async def generate_text(
        self,
        model: str,
        messages: List[Dict[str, str]],
        session: Optional[AsyncSession] = None,
        user_id: Optional[int] = None
    ) -> Optional[str]:
        return await self.text_gen.generate(model, messages, session=session, user_id=user_id)

    async def generate_image(
        self,
        model: str,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
    ) -> Optional[Union[str, BufferedInputFile]]:
        if reference_images is None:
            reference_images = []

        # --- МОДЕЛИ ЧЕРЕЗ OPENROUTER (Nano Banana + GPT Images + Riverflow) ---
        openrouter_image_models = {
            "openai/gpt-5.4-image-2",
            "google/gemini-3.1-flash-image-preview",
            "google/gemini-3-pro-image-preview",
            "google/gemini-2.5-flash-image",
            "sourceful/riverflow-v2.5-pro:free",
        }
        if model in openrouter_image_models:
            size_map = {"1:1": "1024x1024", "9:16": "1024x1792", "16:9": "1792x1024"}
            or_size = size_map.get(aspect_ratio or "1:1", "1024x1024")
            return await openrouter.generate_image(
                model=model,
                prompt=prompt,
                size=or_size,
                reference_images=reference_images,
            )

        # --- ОСТАЛЬНЫЕ image-модели через Polza AI Media API ---
        return await generate_media_image(
            model=model,
            prompt=prompt,
            aspect_ratio=aspect_ratio or "1:1",
            max_images=1,
            reference_images=reference_images,
        )

    async def generate_video(
        self,
        model: str,
        prompt: str,
        image_url: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if extra_params is None:
            extra_params = {}

        logger.info(f"APIClient: Video generation. Model: {model}, Image: {bool(image_url)}")

        # ВСЕ видео-модели через Polza AI Media API
        return await polza_generate_video(
            model=model,
            prompt=prompt,
            image_url=image_url,
            extra_params=extra_params,
            poll_seconds=10,
            max_wait_seconds=1200,
            context=context,
        )

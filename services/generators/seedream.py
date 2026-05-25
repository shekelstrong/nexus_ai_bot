# services/generators/seedream.py
"""Legacy wrapper — Seedream теперь через Polza AI Media API."""
from typing import Optional, Union, List
from aiogram.types import BufferedInputFile
from services.polza_ai import generate_media_image
from utils.logger import logger

class SeedreamGenerator:
    async def generate(
        self,
        model: str,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: Optional[str] = None,
    ) -> Optional[Union[str, BufferedInputFile]]:
        if reference_images is None:
            reference_images = []
        logger.info(f"SeedreamGenerator -> Polza AI: model={model}")
        return await generate_media_image(
            model=model,
            prompt=prompt,
            aspect_ratio=aspect_ratio or "1:1",
            max_images=1,
            reference_images=reference_images,
        )

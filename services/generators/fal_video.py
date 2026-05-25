# services/generators/fal_video.py
"""Legacy FAL AI Video generator — DEPRECATED. All video generation now goes through Polza AI Media API.
This file is kept as a stub for backward compatibility of existing DB records and imports.
"""
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from config import settings
from utils.logger import logger


class FalVideoGenerator:
    """DEPRECATED — use services.polza_ai.generate_video instead."""
    def __init__(self):
        self.api_key = getattr(settings, "FAL_AI_API_KEY", None) or getattr(settings, "POLZA_AI_API_KEY", "")
        self.base_url = "https://queue.fal.run"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def generate(
        self,
        model: str,
        prompt: str,
        image_url: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        logger.warning(f"FalVideoGenerator is DEPRECATED. Redirecting to Polza AI for model={model}")
        from services.polza_ai import generate_video
        return await generate_video(
            model=model,
            prompt=prompt,
            image_url=image_url,
            extra_params=extra_params or {},
            poll_seconds=10,
            max_wait_seconds=1200,
        )

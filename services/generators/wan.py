"""Legacy wrapper — Wan models теперь через Polza AI Media API."""
from typing import Optional, Dict, Any
from services.polza_ai import generate_video
from utils.logger import logger

class WanGenerator:
    async def generate(
        self,
        model_id: str,
        prompt: str,
        image_url: Optional[str] = None,
        extra_params: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> Optional[str]:
        if extra_params is None:
            extra_params = {}
        logger.info(f"WanGenerator -> Polza AI: model={model_id}")
        return await generate_video(
            model=model_id,
            prompt=prompt,
            image_url=image_url,
            extra_params=extra_params,
            poll_seconds=10,
            max_wait_seconds=600,
            context=context,
        )

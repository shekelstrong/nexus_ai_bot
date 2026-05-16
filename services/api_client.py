import aiohttp
from typing import Optional, List, Dict, Union, Any
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from utils.logger import logger

# Импортируем генераторы
from services.generators.standard_text import StandardTextGenerator
from services.generators.seedream import SeedreamGenerator
from services.generators.standard_image import StandardImageGenerator

# Генераторы через Polza.AI (вместо Fal AI)
from services.generators.kling import KlingGenerator
from services.generators.veo import VeoGenerator
from services.generators.wan import WanGenerator


class APIClient:
    def __init__(self):
        self.text_gen = StandardTextGenerator()
        self.seedream_gen = SeedreamGenerator()
        self.std_image_gen = StandardImageGenerator()  # OpenRouter + Polza (Flux)

        # Polza.AI видео-генераторы
        self.kling_gen = KlingGenerator()
        self.veo_gen = VeoGenerator()
        self.wan_gen = WanGenerator()


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
        size: Optional[str] = None
    ) -> Optional[Union[str, BufferedInputFile]]:
        if reference_images is None:
            reference_images = []
        
        model_lower = model.lower()

        if "seedream" in model_lower:
            return await self.seedream_gen.generate(model, prompt, reference_images)

        # Flux модели через Polza.AI Images API
        if "flux" in model_lower or "black-forest" in model_lower or "stable-diffusion" in model_lower:
            from services.polza_ai import generate_image as polza_image
            return await polza_image(model, prompt, size=size)

        # Остальные модели (Gemini, GPT-5 Image, etc.) через OpenRouter
        return await self.std_image_gen.generate(model, prompt, reference_images, size=size)


    async def generate_video(
        self, 
        model: str, 
        prompt: str, 
        image_url: Optional[str] = None, 
        extra_params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        model_lower = model.lower()
        
        if extra_params is None:
            extra_params = {}

        logger.info(f"APIClient: Polza Video. Model: {model}, Image: {bool(image_url)}")

        # Компакт-маппинг: старые model_id из БД → актуальные для Polza
        model = {"kling/v2.6": "kling/v2.5-turbo"}.get(model, model)

        # Поддержка суффикса ::N для фиксированной длительности
        actual_model = model
        if "::" in model:
            base, dur = model.rsplit("::", 1)
            actual_model = base
            if "duration" not in extra_params:
                extra_params["duration"] = dur

        if "seedance" in model_lower:
            return await self.kling_gen.generate(actual_model, prompt, image_url, extra_params, context=context)
        if "kling" in model_lower:
            return await self.kling_gen.generate(actual_model, prompt, image_url, extra_params, context=context)
        if "veo" in model_lower:
            return await self.veo_gen.generate(actual_model, prompt, image_url, extra_params, context=context)
        if "wan" in model_lower:
            return await self.wan_gen.generate(actual_model, prompt, image_url, extra_params, context=context)
        if "luma" in model_lower:
             return await self.wan_gen.generate(actual_model, prompt, image_url, extra_params, context=context) 

        logger.warning(f"APIClient: Unknown video model {model}. Using wan_gen.")
        return await self.wan_gen.generate(actual_model, prompt, image_url, extra_params, context=context)

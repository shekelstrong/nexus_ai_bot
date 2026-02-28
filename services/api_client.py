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

# Новые FAL генераторы
from services.generators.kling import KlingGenerator
from services.generators.veo import VeoGenerator
from services.generators.wan import WanGenerator


class APIClient:
    def __init__(self):
        self.text_gen = StandardTextGenerator()
        self.seedream_gen = SeedreamGenerator()
        self.std_image_gen = StandardImageGenerator() # OpenRouter (Flux, Gemini)

        # FAL
        self.kling_gen = KlingGenerator()
        self.veo_gen = VeoGenerator()
        self.wan_gen = WanGenerator()

        self.fal_key = settings.FAL_AI_API_KEY


    async def generate_text(
        self, 
        model: str, 
        messages: List[Dict[str, str]],
        session: Optional[AsyncSession] = None,
        user_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Генерация текста с поддержкой истории сообщений.
        
        Args:
            model: ID модели
            messages: Список сообщений [{"role": "user", "content": "..."}]
            session: SQLAlchemy сессия (для работы с историей)
            user_id: ID пользователя (для работы с историей)
        """
        return await self.text_gen.generate(model, messages, session=session, user_id=user_id)


    async def generate_image(self, model: str, prompt: str) -> Optional[Union[str, BufferedInputFile]]:
        model_lower = model.lower()
        
        if "seedream" in model_lower:
            return await self.seedream_gen.generate(model, prompt)
            
        # Stable Diffusion через FAL (если нужно, можно добавить отдельный генератор)
        # Пока оставим стандартный генератор, если он поддерживает SD
        return await self.std_image_gen.generate(model, prompt)


    async def generate_video(
        self, 
        model: str, 
        prompt: str, 
        image_url: Optional[str] = None, 
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Универсальный метод для генерации видео.
        Выбирает нужный генератор по названию модели.
        """
        model_lower = model.lower()
        
        if extra_params is None:
            extra_params = {}

        logger.info(f"APIClient: Запрос видео-генерации. Модель: {model}, Image: {bool(image_url)}")

        if "kling" in model_lower:
            return await self.kling_gen.generate(model, prompt, image_url, extra_params)
            
        if "veo" in model_lower:
            return await self.veo_gen.generate(model, prompt, image_url, extra_params)
            
        if "wan" in model_lower:
            return await self.wan_gen.generate(model, prompt, image_url, extra_params)
            
        # Fallback (например Luma, если она работает через Wan API или похожий)
        if "luma" in model_lower:
             return await self.wan_gen.generate(model, prompt, image_url, extra_params) 

        logger.warning(f"APIClient: Неизвестная модель видео '{model}'. Пробую wan_gen как дефолт.")
        return await self.wan_gen.generate(model, prompt, image_url, extra_params)
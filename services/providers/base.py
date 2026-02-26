from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Union, Any
from aiogram.types import BufferedInputFile

class BaseProvider(ABC):
    """
    Базовый класс для всех провайдеров генерации.
    Определяет методы, которые должны быть реализованы.
    """
    
    @abstractmethod
    async def generate_text(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Генерация текста"""
        pass

    @abstractmethod
    async def generate_image(self, model: str, prompt: str, **kwargs) -> Optional[Union[str, BufferedInputFile]]:
        """Генерация изображения"""
        pass
    
    # Для видео пока можно оставить заглушку или реализовать позже
    async def generate_video(self, model: str, prompt: str, **kwargs) -> Optional[str]:
        return None
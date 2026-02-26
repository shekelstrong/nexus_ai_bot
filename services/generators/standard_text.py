# services/generators/standard_text.py
import aiohttp
from typing import List, Dict, Optional
from config import settings
from utils.logger import logger

class StandardTextGenerator:
    def __init__(self):
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.key = settings.OPENROUTER_API_KEY

    async def generate(self, model: str, messages: List[Dict[str, str]]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.WEBHOOK_URL or "https://t.me/NexusAIBot",
            "X-Title": "NexusAI",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        # Если модель "думающая" (o1, r1, reasoning) — добавляем флаг
        if any(x in model for x in ["reasoning", "r1", "o1", "o3"]):
             payload["include_reasoning"] = True

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Text Gen Error {resp.status}: {await resp.text()}")
                        return f"Error: API {resp.status}"
                    
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Text Gen Exception: {e}")
            return None
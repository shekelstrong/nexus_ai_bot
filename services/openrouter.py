import aiohttp
import json
from config import settings
from utils.logger import logger


async def generate_text(model: str, prompt: str) -> str:
    """
    Генерация текста через OpenRouter API.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # "HTTP-Referer": settings.WEBHOOK_URL, # Опционально
        # "X-Title": "NexusAI Bot", # Опционально
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000 # Можно настроить лимит
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter Error: {response.status} - {error_text}")
                    return f"Ошибка API: {response.status}"
                
                result = await response.json()
                
                # Извлекаем текст ответа
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    return "Пустой ответ от нейросети."

    except Exception as e:
        logger.exception(f"Exception in generate_text: {e}")
        return "Произошла ошибка при генерации."


async def generate_image_openrouter(model: str, prompt: str) -> str:
    """
    Генерация изображений через OpenRouter API.
    Фактически для OR это тот же чат-комплишн, но ответ будет ссылкой.
    """
    # Используем ту же логику, что и для текста, так как OR возвращает markdown-ссылку в content
    response = await generate_text(model, prompt)
    
    # Пытаемся извлечь чистую ссылку, если она пришла в Markdown
    # Часто формат такой: ![image](https://...)
    if response and "](" in response and response.endswith(")"):
        try:
            url = response.split("](")[1].rstrip(")")
            return url
        except:
            return response # Возвращаем как есть, если не вышло распарсить
            
    # Если пришла просто ссылка (начинается с http)
    if response and response.strip().startswith("http"):
        return response.strip()
        
    return response # Возвращаем текст ошибки или описание, если это не ссылка
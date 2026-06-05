import aiohttp
from typing import Optional, List
from config import settings
from utils.logger import logger

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_KEY = settings.OPENROUTER_API_KEY


def _headers():
    return {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://nexus-ai.vercel.app",
        "X-Title": "Nexus AI Bot",
    }


async def generate_text(model: str, prompt: str) -> str:
    """
    Генерация текста через OpenRouter API.
    """
    url = f"{OPENROUTER_BASE}/chat/completions"
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4000,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=_headers(), json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter Error: {response.status} - {error_text[:300]}")
                    return f"Ошибка API: {response.status}"
                
                result = await response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    msg = result["choices"][0]["message"]
                    if msg.get("content"):
                        return msg["content"]
                
                logger.warning(f"OpenRouter: unexpected response: {str(result)[:200]}")
                return "Пустой ответ от API"
                
    except Exception as e:
        logger.error(f"OpenRouter exception: {e}")
        return f"Ошибка соединения: {e}"


async def generate_image(
    model: str,
    prompt: str,
    size: str = "1024x1024",
    reference_images: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Генерация изображения через OpenRouter API с modalities=["image"].
    Поддерживает Gemini Nano Banana и GPT Images.
    
    size: OpenRouter image size (1024x1024 | 1024x1792 | 1792x1024)
    reference_images: список URL или base64 строк для image-to-image
    """
    url = f"{OPENROUTER_BASE}/chat/completions"
    
    # Собираем content: текст + референс-изображения
    content_parts = [{"type": "text", "text": prompt}]
    
    if reference_images:
        for ref in reference_images:
            if ref.startswith("data:"):
                content_parts.append({"type": "image_url", "image_url": {"url": ref}})
            else:
                content_parts.append({"type": "image_url", "image_url": {"url": ref}})
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": content_parts,
            }
        ],
        "modalities": ["image"],
    }
    
    # Добавляем size если передан (только для поддерживающих моделей)
    if size:
        payload["size"] = size

    logger.info(f"OpenRouter Image: model={model}, size={size}, refs={len(reference_images or [])}, prompt={prompt[:60]}")

    try:
        timeout = aiohttp.ClientTimeout(total=120, sock_connect=30, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=_headers(), json=payload) as response:
                if response.status != 200:
                    err = await response.text()
                    logger.error(f"OpenRouter Image Error {response.status}: {err[:300]}")
                    return None

                data = await response.json()

                if data.get("choices") and len(data["choices"]) > 0:
                    msg = data["choices"][0].get("message", {})
                    
                    # Новый формат: images[] массив
                    if msg.get("images") and len(msg["images"]) > 0:
                        img_entry = msg["images"][0]
                        img_url = img_entry.get("image_url", {}).get("url")
                        if img_url and img_url.startswith("http"):
                            logger.info(f"OpenRouter Image: URL получен")
                            return img_url
                        # base64 fallback
                        if img_entry.get("content"):
                            return img_entry["content"]
                    
                    # Старый формат: content с markdown-ссылкой ![...](url)
                    content = msg.get("content", "")
                    if content:
                        # Пытаемся извлечь URL из markdown ![...](url)
                        import re
                        match = re.search(r'!\[.*?\]\((https?://[^\)]+)\)', content)
                        if match:
                            return match.group(1)
                        # Если просто URL
                        if content.strip().startswith("http"):
                            return content.strip()
                        # Если base64 data URI
                        if content.strip().startswith("data:image"):
                            return content.strip()
                
                logger.warning(f"OpenRouter Image: нет URL в ответе: {str(data)[:200]}")
                return None
                
    except Exception as e:
        logger.error(f"OpenRouter Image exception: {e}")
        return None

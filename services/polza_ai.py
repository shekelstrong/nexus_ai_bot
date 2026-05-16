"""
Polza.AI API Client — универсальный клиент для Polza.ai
Заменяет fal_ai.py (Fal AI)
Поддерживает:
- Текст: POST /api/v1/chat/completions (OpenAI-совместимый)
- Изображения: POST /api/v2/images/generations
- Медиа/Видео: POST /api/v1/media (асинхронно)
- Загрузка файлов: POST /api/v1/files/upload
"""
import aiohttp
import asyncio
from typing import Optional, List, Dict, Any, Union
from aiogram.types import BufferedInputFile

from config import settings
from utils.logger import logger
from utils.headers import get_headers as _headers

# Отслеживание активных поллов для восстановления после рестарта
import json
import os
import time
_ACTIVE_POLLS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "active_polls.json")

def _save_active_poll(media_id: str, context: dict):
    entry = {"media_id": media_id, "timestamp": time.time()}
    entry.update(context)
    with open(_ACTIVE_POLLS_FILE, "a") as f:
        json.dump(entry, f)
        f.write("\n")

def _load_active_polls():
    if not os.path.exists(_ACTIVE_POLLS_FILE):
        return []
    polls = []
    with open(_ACTIVE_POLLS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    polls.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return polls

def _clear_active_poll(media_id: str):
    if not os.path.exists(_ACTIVE_POLLS_FILE):
        return
    with open(_ACTIVE_POLLS_FILE) as f:
        lines = f.readlines()
    with open(_ACTIVE_POLLS_FILE, "w") as f:
        for line in lines:
            if media_id not in line:
                f.write(line)

POLZA_BASE_URL = "https://polza.ai/api"
POLZA_CHAT_URL = f"{POLZA_BASE_URL}/v1/chat/completions"
POLZA_IMAGE_URL = f"{POLZA_BASE_URL}/v2/images/generations"
POLZA_MEDIA_URL = f"{POLZA_BASE_URL}/v1/media"
POLZA_MEDIA_STATUS_URL = POLZA_BASE_URL + "/v1/media/{}/status"
POLZA_FILE_UPLOAD_URL = f"{POLZA_BASE_URL}/v1/storage/upload"  # Был /v1/files/upload — неправильный! (см. docs https://polza.ai/docs/api-reference/storage/upload)


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.POLZA_AI_API_KEY}",
        "Content-Type": "application/json",
    }


async def upload_file(file_bytes: bytes, filename: str, content_type: str) -> Optional[str]:
    """
    Загружает файл в хранилище Polza.AI и возвращает URL.
    Используется для image-to-video и других задач.
    """
    if not file_bytes:
        logger.error("Polza Upload: file_bytes is None")
        return None

    file_size_mb = len(file_bytes) / (1024 * 1024)
    logger.info(f"Polza Upload: {filename}, {file_size_mb:.2f}MB")

    try:
        timeout = aiohttp.ClientTimeout(total=300, sock_connect=60, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            form = aiohttp.FormData()
            form.add_field("file", file_bytes, filename=filename, content_type=content_type)
            headers = {"Authorization": f"Bearer {settings.POLZA_AI_API_KEY}"}
            async with session.post(POLZA_FILE_UPLOAD_URL, headers=headers, data=form) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    url = data.get("url") or data.get("data", {}).get("url")
                    if url:
                        logger.info(f"Polza Upload успешен: {url}")
                        return url
                else:
                    logger.warning(f"Polza Upload ошибка {resp.status}: {(await resp.text())[:200]}")
        return None
    except Exception as e:
        logger.error(f"Polza Upload exception: {e}")
        return None


async def submit_media(model: str, payload: Dict[str, Any], async_mode: bool = True) -> Optional[Dict[str, Any]]:
    """
    Отправляет задачу на генерацию медиа (видео/аудио/изображения)
    через Polza.AI Media API.
    
    Args:
        model: ID модели (kling/v2.6, wan/2.6, google/veo3, etc.)
        payload: Параметры генерации {prompt, images, aspect_ratio, ...}
        async_mode: True=асинхронно (нужен poll), False=синхронно
    """
    url = POLZA_MEDIA_URL
    body = {
        "model": model,
        "input": payload,
        "async": async_mode,
    }

    logger.info(f"Polza Media Submit: model={model}, async={async_mode}")

    try:
        timeout = aiohttp.ClientTimeout(total=600, sock_connect=120, sock_read=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=_headers(), json=body) as resp:
                if resp.status not in (200, 201):
                    err = await resp.text()
                    logger.error(f"Polza Media Error {resp.status}: {err[:300]}")
                    return None
                data = await resp.json()
                logger.info(f"Polza Media response keys: {list(data.keys()) if isinstance(data, dict) else not-dict}")
                return data
    except Exception as e:
        logger.error(f"Polza Media exception: {e}")
        return None


async def poll_media(media_id: str, poll_seconds: int = 5, max_wait_seconds: int = 600) -> Optional[Dict[str, Any]]:
    """
    Поллинг статуса медиа-генерации.
    """
    url = POLZA_MEDIA_STATUS_URL.format(media_id)
    logger.info(f"Polza Poll: start polling {media_id}, max {max_wait_seconds}s")

    start = asyncio.get_running_loop().time()
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                elapsed = asyncio.get_running_loop().time() - start
                if elapsed > max_wait_seconds:
                    logger.error(f"Polza Poll: timeout {max_wait_seconds}s")
                    return None

                await asyncio.sleep(poll_seconds)
                try:
                    async with session.get(url, headers=_headers()) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                        status = data.get("status", "").upper()

                        if status == "COMPLETED":
                            logger.info(f"Polza Poll: COMPLETED after {int(elapsed)}s")
                            return data
                        elif status == "FAILED":
                            logger.error(f"Polza Poll: FAILED: {data.get('error', 'unknown')}")
                            return None
                        # IN_QUEUE, IN_PROGRESS, PROCESSING — продолжаем
                except Exception as e:
                    logger.warning(f"Polza Poll check error: {e}")
                    continue
    except Exception as e:
        logger.error(f"Polza Poll exception: {e}")
        return None


def extract_media_url(data: Dict[str, Any]) -> Optional[str]:
    """Извлекает URL медиа из ответа Polza.AI в разных форматах."""
    if not isinstance(data, dict):
        return None

    # Прямой URL в ответе
    for key in ["url", "video_url", "audio_url", "image_url"]:
        val = data.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val

    # Вложенные объекты
    for key in ["video", "audio", "image", "file"]:
        val = data.get(key)
        if isinstance(val, dict):
            url = val.get("url")
            if url:
                return url

    # Массив результатов или объект с url
    for key in ["images", "videos", "data", "output"]:
        val = data.get(key)
        if isinstance(val, dict):
            url = val.get("url")
            if url:
                return url
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, dict):
                url = first.get("url") or first.get("video_url") or first.get("image_url")
                if url:
                    return url
            elif isinstance(first, str) and first.startswith("http"):
                return first

    # Глубокий поиск
    if "output" in data:
        output = data["output"]
        if isinstance(output, dict):
            return extract_media_url(output)

    # Polling ответ может иметь result / response вложенный
    for key in ["result", "response"]:
        val = data.get(key)
        if isinstance(val, dict):
            url = extract_media_url(val)
            if url:
                return url

    return None


async def generate_image(model: str, prompt: str, size: Optional[str] = None) -> Optional[str]:
    """
    Генерация изображения через Polza.AI Images API.
    OpenAI-совместимый DALL-E стиль.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "response_format": "url",
    }
    if size:
        payload["size"] = size

    logger.info(f"Polza Image: model={model}, prompt={prompt[:50]}")

    try:
        timeout = aiohttp.ClientTimeout(total=120, sock_connect=30, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(POLZA_IMAGE_URL, headers=_headers(), json=payload) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error(f"Polza Image Error {resp.status}: {err[:300]}")
                    return None
                data = await resp.json()
                if data.get("data") and len(data["data"]) > 0:
                    url = data["data"][0].get("url")
                    if url:
                        logger.info(f"Polza Image успешно: {url[:80]}")
                        return url
                logger.warning(f"Polza Image: нет URL в ответе: {str(data)[:200]}")
                return None
    except Exception as e:
        logger.error(f"Polza Image exception: {e}")
        return None


async def generate_video(
    model: str,
    prompt: str,
    image_url: Optional[str] = None,
    extra_params: Optional[Dict[str, Any]] = None,
    poll_seconds: int = 10,
    max_wait_seconds: int = 600,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Генерация видео через Polza.AI Media API.
    
    context: опциональный словарь с user_db_id, telegram_id, gen_id для персистентности полла.
    """
    if extra_params is None:
        extra_params = {}

    payload: Dict[str, Any] = {
        "prompt": prompt,
        "aspect_ratio": extra_params.get("aspect_ratio", "16:9"),
    }

    # Image-to-Video — автоопределение: base64 data URL или обычный URL
    if image_url:
        if image_url.startswith("data:"):
            payload["images"] = [{"type": "base64", "data": image_url}]
        else:
            payload["images"] = [{"type": "url", "data": image_url}]

    # Дополнительные параметры
    if "duration" in extra_params:
        payload["duration"] = extra_params["duration"]
    if "second_image_url" in extra_params:
        # Veo First-Last-Frame — определяем тип автоматически
        second_url = extra_params["second_image_url"]
        if "images" not in payload:
            payload["images"] = []
        if second_url.startswith("data:"):
            payload["images"].append({"type": "base64", "data": second_url})
        else:
            payload["images"].append({"type": "url", "data": second_url})
    if "cfg_scale" in extra_params:
        payload["cfg_scale"] = extra_params["cfg_scale"]
    if "video_url" in extra_params:
        # Motion control reference video — определяем тип автоматически
        video_ref_url = extra_params["video_url"]
        if "images" not in payload:
            payload["images"] = []
        if video_ref_url.startswith("data:"):
            payload["images"].append({"type": "base64", "data": video_ref_url})
        else:
            payload["images"].append({"type": "url", "data": video_ref_url})

    # Параметры, которые обработаны выше (не копировать повторно)
    _handled = {"aspect_ratio", "duration", "cfg_scale", "second_image_url", "video_url"}
    for k, v in extra_params.items():
        if k not in _handled and k not in payload:
            payload[k] = v

    logger.info(f"Polza Video: model={model}, image={bool(image_url)}, params={list(payload.keys())}")

    # Отправляем асинхронно
    result = await submit_media(model, payload, async_mode=True)
    if not result:
        return None

    # Пробуем сразу достать URL (синхронный ответ)
    url = extract_media_url(result)
    if url:
        logger.info(f"Polza Video: быстрый URL получен")
        return url

    # Иначе — поллинг
    media_id = result.get("id") or result.get("media_id") or result.get("request_id")
    if not media_id:
        logger.error(f"Polza Video: нет ID для поллинга. Ответ: {str(result)[:200]}")
        return None

    # Сохраняем активный полл для восстановления после рестарта
    _save_active_poll(media_id, context or {})

    poll_result = await poll_media(media_id, poll_seconds=poll_seconds, max_wait_seconds=max_wait_seconds)
    if not poll_result:
        _clear_active_poll(media_id)
        return None

    url = extract_media_url(poll_result)
    if url:
        _clear_active_poll(media_id)
        return url

    # Fallback: response_url
    response_url = poll_result.get("response_url")
    if response_url:
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(response_url, headers=_headers()) as resp:
                    if resp.status == 200:
                        final = await resp.json()
                        url = extract_media_url(final)
                        if url:
                            return url
        except Exception as e:
            logger.warning(f"Polza Video response_url fetch: {e}")

    logger.error(f"Polza Video: не удалось извлечь URL")
    return None


async def generate_text(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> Optional[str]:
    """
    Генерация текста через Polza.AI Chat Completions API.
    OpenAI-совместимый.
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    logger.info(f"Polza Text: model={model}, messages={len(messages)}")

    try:
        timeout = aiohttp.ClientTimeout(total=120, sock_connect=30, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(POLZA_CHAT_URL, headers=_headers(), json=payload) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error(f"Polza Text Error {resp.status}: {err[:300]}")
                    return None
                data = await resp.json()
                if data.get("choices") and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    return content
                logger.warning(f"Polza Text: пустой ответ")
                return None
    except Exception as e:
        logger.error(f"Polza Text exception: {e}")
        return None

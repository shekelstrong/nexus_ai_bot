"""
Supabase Storage для загрузки фото и видео.
Используем REST API напрямую (без библиотеки supabase-py).
Бесплатно, безлимитно на фото/видео до 2GB хранилища.
"""

import aiohttp
import mimetypes
from typing import Optional
from config import settings
from utils.logger import logger

SUPABASE_URL = "https://rakkojwkwkrrefxjpkgi.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJha2tvandrd2tycmVmeGpwa2dpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Njg5MDc1MCwiZXhwIjoyMDkyNDY2NzUwfQ.yXv1qAlnrJ9OSt6Krn7PJmjs_AhQjYzWz9lPKvcC8mo"

BUCKET_NAME = "product-images"
MAX_RETRIES = 3


async def ensure_bucket_exists():
    """Проверяет что bucket существует, если нет — создаёт."""
    url = f"{SUPABASE_URL}/storage/v1/bucket/{BUCKET_NAME}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return True
                # Bucket не существует — создаём
                if resp.status in (404, 400):
                    create_url = f"{SUPABASE_URL}/storage/v1/bucket"
                    create_body = {
                        "id": BUCKET_NAME,
                        "name": BUCKET_NAME,
                        "public": True,
                        "file_size_limit": 52428800,  # 50MB
                        "allowed_mime_types": [
                            "image/jpeg", "image/png", "image/webp",
                            "video/mp4", "video/quicktime"
                        ],
                    }
                    async with session.post(create_url, headers=headers, json=create_body) as cr:
                        if cr.status in (200, 201, 409):  # 409 = already exists
                            return True
                        logger.warning(f"Supabase create bucket failed: {cr.status}")
                        return False
    except Exception as e:
        logger.error(f"Supabase ensure_bucket error: {e}")
        return False


async def upload_file(
    file_bytes: bytes,
    file_path: str,
    content_type: Optional[str] = None,
) -> Optional[str]:
    """
    Загружает файл в Supabase Storage.
    
    Args:
        file_bytes: Содержимое файла
        file_path: Путь в бакете (например "photos/file_id.jpg")
        content_type: MIME-тип (автоопределение если не указан)
    
    Returns:
        Публичный URL файла или None при ошибке
    """
    if not content_type:
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "application/octet-stream"

    size_mb = len(file_bytes) / (1024 * 1024)
    logger.info(f"Supabase upload: {file_path}, {size_mb:.2f}MB, type={content_type}")

    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{file_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    for attempt in range(MAX_RETRIES):
        try:
            timeout = aiohttp.ClientTimeout(total=300, sock_connect=30, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, data=file_bytes) as resp:
                    if resp.status in (200, 201):
                        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"
                        logger.info(f"Supabase upload OK: {public_url}")
                        return public_url

                    if resp.status == 404:
                        # Bucket может не быть — создаём
                        await ensure_bucket_exists()
                        continue

                    error_text = await resp.text()
                    logger.warning(f"Supabase upload attempt {attempt+1} failed: {resp.status} - {error_text[:200]}")

        except Exception as e:
            logger.warning(f"Supabase upload attempt {attempt+1} error: {e}")

        if attempt < MAX_RETRIES - 1:
            import asyncio
            await asyncio.sleep(1)

    logger.error(f"Supabase upload failed after {MAX_RETRIES} attempts: {file_path}")
    return None


async def upload_photo(file_bytes: bytes, file_id: str) -> Optional[str]:
    """
    Загружает фото в Supabase Storage.
    
    Args:
        file_bytes: Содержимое файла
        file_id: Telegram file_id (используется как имя файла)
    
    Returns:
        Публичный URL или None
    """
    file_path = f"photos/{file_id}.jpg"
    return await upload_file(file_bytes, file_path, "image/jpeg")


async def upload_video(file_bytes: bytes, file_id: str) -> Optional[str]:
    """
    Загружает видео в Supabase Storage.
    
    Args:
        file_bytes: Содержимое файла
        file_id: Telegram file_id
    
    Returns:
        Публичный URL или None
    """
    file_path = f"videos/{file_id}.mp4"
    return await upload_file(file_bytes, file_path, "video/mp4")


async def delete_file(file_path: str) -> bool:
    """Удаляет файл из Supabase Storage."""
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{file_path}"
    headers = {"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                return resp.status in (200, 204)
    except Exception as e:
        logger.error(f"Supabase delete error: {e}")
        return False

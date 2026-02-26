import aiohttp
import asyncio
from typing import Optional
from config import settings
from utils.logger import logger

async def upload_file_to_fal(file_bytes: bytes, filename: str, content_type: str) -> Optional[str]:
    """
    Uploads a file to fal storage and returns a public access URL.
    Использует официальный Python клиент Fal AI для загрузки файлов.
    
    Согласно документации Fal AI:
    - Можно использовать fal_client.upload_file() для загрузки файлов
    - API поддерживает до 100MB для видео
    - motion-control модель поддерживает .mp4/.mov, ≤100MB, 2-60s, 720p/1080p only
    """
    if not file_bytes:
        logger.error("FAL Upload: file_bytes is None or empty")
        return None

    file_size_mb = len(file_bytes) / (1024 * 1024)
    logger.info(f"FAL Upload: файл {filename}, тип={content_type}, размер={file_size_mb:.2f}MB ({len(file_bytes)} bytes)")
    
    try:
        # Сохраняем байты во временный файл и используем fal_client
        import tempfile
        import os
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name
        
        # Используем fal_client для загрузки файла
        try:
            from fal_client import SyncClient
            logger.info(f"FAL Upload: загрузка файла через fal_client.SyncClient")
            
            # Создаем кастомный клиент с увеличенным таймаутом (10 минут)
            client = SyncClient(key=settings.FAL_AI_API_KEY, default_timeout=600.0)
            
            # Загружаем файл через кастомный клиент Fal AI
            url = client.upload_file(temp_file_path)
            
            logger.info(f"FAL Upload успешен: {url}")
            return url
        except Exception as e:
            logger.warning(f"fal_client.SyncClient не удался: {type(e).__name__}: {e}")
            logger.info("Пробуем альтернативный метод...")
            
            # Fallback: прямой HTTP запрос к API Fal AI
            headers = {"Authorization": f"Key {settings.FAL_AI_API_KEY}"}
            # Правильный URL для загрузки файлов через Fal AI
            upload_url = "https://queue.fal.run/files"
            
            logger.info(f"FAL Upload fallback: отправка файла на {upload_url}")
            
            form = aiohttp.FormData()
            form.add_field("file", file_bytes, filename=filename, content_type=content_type)
            
            # Увеличиваем timeout для больших файлов (до 5 минут)
            timeout = aiohttp.ClientTimeout(total=300, sock_connect=60, sock_read=60)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(upload_url, headers=headers, data=form) as resp:
                    logger.info(f"FAL Upload fallback response: статус {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        access_url = data.get("access_url")
                        if access_url:
                            logger.info(f"FAL Upload fallback успешен: access_url={access_url}")
                            return access_url
                    else:
                        error_text = await resp.text()
                        logger.warning(f"FAL Upload fallback не удался {resp.status}: {error_text[:200]}")
        finally:
            # Удаляем временный файл
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass

        logger.warning("FAL Upload v3 не удался, пробуем альтернативный метод")
        
        # Попытка 2: прямой upload через fal.run с Bearer token
        timeout = aiohttp.ClientTimeout(total=300, sock_connect=60, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            auth_url = "https://rest.alpha.fal.ai/storage/auth/token?storage_type=fal-cdn-v3"
            async with session.post(auth_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    token = data.get("token")
                    base_url = data.get("base_url")
                    if token and base_url:
                        upload_url = f"{base_url}/files/upload"
                        form = aiohttp.FormData()
                        form.add_field("file", file_bytes, filename=filename, content_type=content_type)
                        async with session.post(
                            upload_url,
                            data=form,
                            headers={"Authorization": f"Bearer {token}"},
                        ) as resp:
                            if resp.status == 200:
                                up = await resp.json()
                                access_url = up.get("access_url")
                                if access_url:
                                    logger.info(f"FAL Upload v2 (token) успешен: access_url={access_url}")
                                    return access_url
                            else:
                                error_text = await resp.text()
                                logger.warning(f"FAL Upload v2 (token) не удался {resp.status}: {error_text[:200]}")
                else:
                    error_text = await resp.text()
                    logger.warning(f"FAL Auth не удался {resp.status}: {error_text[:200]}")

        logger.error("FAL Upload: все методы неудачны, возвращаем None")
        return None

    except aiohttp.ClientError as e:
        logger.error(f"FAL Upload network error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Fal storage upload exception:")
        return None

async def submit_fal_request(endpoint_id: str, arguments: dict):
    """Отправляет задачу в FalAI"""
    # endpoint_id приходит в формате "fal-ai/flux/dev" -> URL "https://fal.run/fal-ai/flux/dev"
    url = f"https://fal.run/{endpoint_id}"
    
    headers = {
        "Authorization": f"Key {settings.FAL_AI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Логируем payload для отладки
    payload_size_kb = len(str(arguments)) / 1024
    logger.info(f"FalAI Submit: {endpoint_id}, payload size: {payload_size_kb:.2f}KB, keys: {list(arguments.keys())}")
    
    # Увеличиваем timeout для больших запросов (до 10 минут)
    timeout = aiohttp.ClientTimeout(total=600, sock_connect=120, sock_read=120)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=arguments) as response:
            if response.status not in (200, 201):
                text = await response.text()
                logger.error(f"FalAI Submit Error: {response.status} - {text}")
                
                # Детальный анализ ошибки 422 (validation error)
                if response.status == 422:
                    try:
                        error_json = response.json() if hasattr(response, 'json') else None
                        if error_json:
                            logger.error(f"Validation error details: {error_json}")
                    except:
                        pass
                
                return None
            return await response.json()

async def generate_image(model: str, prompt: str, aspect_ratio: str = "square_hd") -> Optional[str]:
    """Генерация изображения (Flux и др.)"""
    # aspect_ratio: square_hd, 16:9, etc. - зависит от модели, пока ставим дефолт
    
    # Подгоняем размер под формат Flux (он любит image_size)
    arguments = {
        "prompt": prompt,
        "image_size": "landscape_4_3", # Можно сделать параметром
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "num_images": 1,
        "enable_safety_checker": False
    }
    
    result = await submit_fal_request(model, arguments)
    
    if result and "images" in result:
        return result["images"][0]["url"]
    return None

async def generate_video_from_text(model: str, prompt: str) -> Optional[str]:
    """Генерация видео из текста (Kling, Veo)"""
    arguments = {
        "prompt": prompt,
        "duration": "5" # Kling поддерживает 5 или 10
    }
    
    result = await submit_fal_request(model, arguments)
    
    # Для видео FalAI часто возвращает результат сразу или ссылку на статус
    # Простейшая обработка для синхронных эндпоинтов (как Kling v1):
    if result and "video" in result:
        return result["video"]["url"]
    return None

# Для Image-to-Video нам нужно сначала загрузить картинку на сервер FalAI
# Но пока пропустим этот шаг, так как это требует отдельной функции upload

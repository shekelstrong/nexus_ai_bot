import aiohttp
import asyncio
import json
import re
from typing import Optional, Dict
from config import settings
from utils.logger import logger

class VeoGenerator:
    def __init__(self):
        self.api_key = settings.FAL_AI_API_KEY
        self.base_url = "https://queue.fal.run"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate(self, model_id: str, prompt: str, image_url: Optional[str] = None, extra_params: Optional[Dict] = None) -> Optional[str]:
        """
        Генерация для Google Veo 3.1
        """
        safe_prompt = prompt if prompt and prompt.strip() else "Smoothly and naturally animate the transition between the first and last frame, keeping high realism."
        payload = {"prompt": safe_prompt}

        if "first-last" in model_id:
            if not image_url: return None
            payload["first_frame_url"] = image_url
            
            end_url = extra_params.get("second_image_url") if extra_params else None
            if not end_url:
                logger.warning("Veo First-Last: No second image")
                return None
            payload["last_frame_url"] = end_url

        elif "image-to-video" in model_id or "reference-to-video" in model_id:
            if not image_url: return None
            payload["image_url"] = image_url

        else:
            aspect_ratio = extra_params.get("aspect_ratio", "16:9") if extra_params else "16:9"
            payload["aspect_ratio"] = aspect_ratio

        return await self._submit_and_poll(model_id, payload)

    @staticmethod
    def _extract_video_url(data: Dict) -> Optional[str]:
        """Извлекает URL видео из любого формата ответа FAL."""
        if not isinstance(data, dict):
            return None

        # 1. video: { url: ... }
        vid = data.get("video")
        if isinstance(vid, dict):
            url = vid.get("url")
            if url:
                return url
        elif isinstance(vid, str):
            return vid

        # 2. video_url
        if "video_url" in data and isinstance(data["video_url"], str):
            return data["video_url"]

        # 3. images: [{ url: ... }]
        images = data.get("images")
        if isinstance(images, list) and images:
            img = images[0]
            if isinstance(img, dict):
                return img.get("url")
            elif isinstance(img, str):
                return img

        # 4. file: { url: ... }  (некоторые FAL модели)
        f = data.get("file")
        if isinstance(f, dict):
            return f.get("url")

        # 5. url
        if "url" in data and isinstance(data["url"], str):
            return data["url"]

        return None

    async def _submit_and_poll(self, model_id: str, payload: Dict) -> Optional[str]:
        try:
            timeout = aiohttp.ClientTimeout(total=600, sock_connect=120, sock_read=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                submit_url = f"{self.base_url}/{model_id}"
                logger.info(f"Veo Submitting payload to {submit_url}")
                
                async with session.post(submit_url, headers=self.headers, json=payload) as resp:
                    if resp.status not in [200, 201]:
                        error_text = await resp.text()
                        logger.error(f"Veo Error {resp.status}: {error_text}")
                        return None
                    data = await resp.json()
                    
                if "video" in data:
                    return data["video"].get("url")
                if "video_url" in data:
                    return data["video_url"]

                request_id = data.get("request_id")
                if not request_id: 
                    logger.error(f"Veo no request_id. Data: {data}")
                    return None
                
                status_url = data.get("status_url") or f"{self.base_url}/{model_id}/requests/{request_id}/status"
                logger.info(f"Veo Polling status at {status_url}")
                
                for _ in range(120):
                    await asyncio.sleep(5)
                    try:
                        async with session.get(status_url, headers=self.headers) as resp:
                            if resp.status != 200: 
                                continue
                            
                            data = await resp.json()
                            status = data.get("status")
                            
                            if status == "COMPLETED":
                                logger.info("Veo generation COMPLETED!")
                                url = self._extract_video_url(data)
                                
                                # FAL Queue API: результат лежит по response_url, а не в status-ответе
                                if not url and "response_url" in data:
                                    logger.info(f"Fetching final result from {data['response_url']}")
                                    try:
                                        async with session.get(data["response_url"], headers=self.headers, 
                                                timeout=aiohttp.ClientTimeout(total=120)) as res_resp:
                                            if res_resp.status == 200:
                                                final_data = await res_resp.json()
                                                logger.info(f"Veo response_url data keys: {list(final_data.keys()) if isinstance(final_data, dict) else 'not-dict'}")
                                                url = self._extract_video_url(final_data)
                                                
                                                # Fallback: ищем MP4 в сырых данных
                                                if not url:
                                                    raw = json.dumps(final_data)
                                                    match = re.search(r'(https?://[^\s"]+\.mp4[^\s"]*)', raw)
                                                    if match: url = match.group(1)
                                    except Exception as fetch_e:
                                        logger.warning(f"Veo response_url fetch error: {fetch_e}")
                                
                                # Тотальный fallback — regex по всем данным
                                if not url:
                                    raw = json.dumps(data)
                                    match = re.search(r'(https?://[^\s"]+\.mp4[^\s"]*)', raw)
                                    if match: url = match.group(1)

                                if url:
                                    logger.info(f"Veo Extracted URL: {url}")
                                else:
                                    logger.error(f"Veo could not find video URL. Full data: {json.dumps(data)[:500]}")
                                
                                return url

                            elif status == "FAILED":
                                err = data.get('error', data.get('detail', 'Unknown'))
                                logger.error(f"Veo Task Failed: {err}")
                                return None
                    except Exception as poll_e:
                        logger.warning(f"Veo Poll exception (ignoring): {poll_e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Veo Exception: {e}")
            return None
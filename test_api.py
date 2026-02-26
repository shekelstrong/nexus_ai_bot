import aiohttp
import asyncio
import json
import os

# Берем ключ из .env / окружения
API_KEY = os.getenv("OPENROUTER_API_KEY", "")

async def test_gemini():
    print("--- TESTING GEMINI (NANO BANANA) ---")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://test.local", 
    }
    
    # 1. Тест основной модели
    model = "google/gemini-3-pro-image-preview"
    data = {
        "model": model,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Draw a red cat"}]}]
    }
    
    async with aiohttp.ClientSession() as session:
        print(f"Sending request to {model}...")
        async with session.post(url, headers=headers, json=data) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response: {text[:500]}") # Первые 500 символов

async def test_dalle():
    print("\n--- TESTING OPENAI IMAGE (DALL-E) ---")
    url = "https://openrouter.ai/api/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://test.local", 
    }
    
    # Пробуем стандартную DALL-E 3, которая точно должна быть
    model = "openai/dall-e-3" 
    data = {
        "model": model,
        "prompt": "A cute robot",
    }
    
    async with aiohttp.ClientSession() as session:
        print(f"Sending request to {model}...")
        async with session.post(url, headers=headers, json=data) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response: {text[:500]}")

async def main():
    await test_gemini()
    await test_dalle()

if __name__ == "__main__":
    asyncio.run(main())

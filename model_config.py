# model_config.py

# Каталог моделей с группировкой по категориям и семействам
MODEL_CATALOG = {
    "gen_text": {
        "openai": {
            "models": [
                {"id": "openai/gpt-5-turbo", "name": "GPT-5 Turbo", "cost": 10},
                {"id": "openai/gpt-4o", "name": "GPT-4o", "cost": 5},
                {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "cost": 1},
                {"id": "openai/o3-mini", "name": "OpenAI o3-mini", "cost": 3},
                {"id": "openai/o1", "name": "OpenAI o1", "cost": 8},
            ]
        },
        "anthropic": {
            "models": [
                {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "cost": 5},
                {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "cost": 15},
                {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "cost": 1},
            ]
        },
        "google": {
            "models": [
                {"id": "google/gemini-pro-1.5", "name": "Gemini 1.5 Pro", "cost": 3},
                {"id": "google/gemini-flash-1.5", "name": "Gemini 1.5 Flash", "cost": 1},
            ]
        },
        "deepseek": {
            "models": [
                {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "cost": 2},
                {"id": "deepseek/deepseek-v3", "name": "DeepSeek V3", "cost": 2},
            ]
        },
        "meta": {
            "models": [
                {"id": "meta-llama/llama-3.1-405b", "name": "Llama 3.1 405B", "cost": 3},
                {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "cost": 1},
            ]
        },
         "mistral": {
            "models": [
                {"id": "mistralai/mistral-large-2411", "name": "Mistral Large 2 (Nov)", "cost": 3},
            ]
        },
        "xai": {
            "models": [
                {"id": "x-ai/grok-2-vision-1212", "name": "Grok 2 Vision", "cost": 4},
            ]
        },
        # Perplexity и прочие поисковики
        "perplexity": {
            "models": [
                 {"id": "perplexity/sonar-reasoning-pro", "name": "Perplexity Sonar Reasoning Pro", "cost": 5},
                 {"id": "perplexity/sonar-reasoning", "name": "Perplexity Sonar Reasoning", "cost": 2},
                 {"id": "perplexity/sonar-pro", "name": "Perplexity Sonar Pro", "cost": 3},
                 {"id": "perplexity/sonar", "name": "Perplexity Sonar", "cost": 1},
            ]
        }
    },
    
    "gen_image": {
        "flux": {
            "models": [
                 {"id": "black-forest-labs/flux.2-pro", "name": "Flux 2.0 Pro", "cost": 4},
                 {"id": "black-forest-labs/flux.2-max", "name": "Flux 2.0 Max", "cost": 4},
                 {"id": "black-forest-labs/flux.2-flex", "name": "Flux 2.0 Flex", "cost": 2},
                 {"id": "black-forest-labs/flux.2-klein-4b", "name": "Flux 2.0 Klein", "cost": 1},
                 {"id": "sourceful/riverflow-v2-max-preview", "name": "Riverflow v2 Max", "cost": 3},
                 {"id": "sourceful/riverflow-v2-standard-preview", "name": "Riverflow v2 Standard", "cost": 2},
                 {"id": "sourceful/riverflow-v2-fast-preview", "name": "Riverflow v2 Fast", "cost": 1},
                 # Новая модель из списка
                 {"id": "fal-ai/stable-diffusion-v35-large", "name": "Stable Diffusion v3.5 Large", "cost": 3},
            ]
        },
        "midjourney": {
             "models": [
                {"id": "bytedance-seed/seedream-4.5", "name": "Seedream 4.5 (MJ Style)", "cost": 3},
             ]
        },
        "dalle": {
            "models": [
                 {"id": "openai/dall-e-3", "name": "DALL-E 3", "cost": 8},
                 {"id": "google/gemini-3-pro-image-preview", "name": "Nano Banana PRO", "cost": 5},
                 {"id": "google/gemini-2.5-flash-image", "name": "Nano Banana Free", "cost": 0, "weekly_limit": 100},
            ]
        },
    },

    "gen_video": {
        "kling": {
            "models": [
                {"id": "fal-ai/kling-video/v2.6/pro/text-to-video", "name": "Kling 2.6 Pro (Text)", "cost": 35},
                {"id": "fal-ai/kling-video/v2.6/pro/image-to-video", "name": "Kling 2.6 Pro (Img2Vid)", "cost": 35},
                # Motion Control - отдельный endpoint для v2.6
                {"id": "fal-ai/kling-video/v2.6/pro/motion-control", "name": "Kling 2.6 Pro (Motion)", "cost": 35},
                {"id": "fal-ai/kling-video/v2.6/standard/motion-control", "name": "Kling 2.6 Std (Motion)", "cost": 20},
            ]
        },
        "veo": {
            "models": [
                {"id": "fal-ai/veo3.1", "name": "Veo 3.1 (Text)", "cost": 30},
                {"id": "fal-ai/veo3.1/image-to-video", "name": "Veo 3.1 (Img2Vid)", "cost": 30},
                {"id": "fal-ai/veo3.1/extend-video", "name": "Veo 3.1 (Extend)", "cost": 30},
                {"id": "fal-ai/veo3.1/reference-to-video", "name": "Veo 3.1 (Ref2Vid)", "cost": 30},
                {"id": "fal-ai/veo3.1/first-last-frame-to-video", "name": "Veo 3.1 (First-Last)", "cost": 30},
                
                {"id": "fal-ai/veo3.1/fast", "name": "Veo 3.1 Fast (Text)", "cost": 15},
                {"id": "fal-ai/veo3.1/fast/image-to-video", "name": "Veo 3.1 Fast (Img2Vid)", "cost": 15},
                {"id": "fal-ai/veo3.1/fast/extend-video", "name": "Veo 3.1 Fast (Extend)", "cost": 15},
                {"id": "fal-ai/veo3.1/fast/first-last-frame-to-video", "name": "Veo 3.1 Fast (First-Last)", "cost": 15},
            ]
        },
        "wan": {
             "models": [
                {"id": "wan/v2.6/text-to-video", "name": "Wan 2.6 (Text)", "cost": 25},
                {"id": "wan/v2.6/image-to-video", "name": "Wan 2.6 (Img2Vid)", "cost": 25},
                {"id": "wan/v2.6/reference-to-video", "name": "Wan 2.6 (Ref2Vid)", "cost": 25},
             ]
        },
        "luma": {
            "models": [
                 {"id": "luma/photon", "name": "Luma Photon (Flash)", "cost": 2},
                 {"id": "luma/photon-pro", "name": "Luma Photon (Pro)", "cost": 5},
            ]
        },
    },

    "gen_search": {
        "perplexity": {
            "models": [
                {"id": "perplexity/sonar-reasoning-pro", "name": "Perplexity Sonar Reasoning Pro", "cost": 5},
                {"id": "perplexity/sonar-reasoning", "name": "Perplexity Sonar Reasoning", "cost": 2},
                {"id": "perplexity/sonar-pro", "name": "Perplexity Sonar Pro", "cost": 3},
                {"id": "perplexity/sonar", "name": "Perplexity Sonar", "cost": 1},
            ]
        }
    }
}
# model_config.py

# Каталог моделей с группировкой по категориям и семействам
MODEL_CATALOG = {
    "gen_text": {
        "openai": {
            "models": [
                {"id": "openai/gpt-5", "name": "GPT-5", "cost": 15},
                {"id": "openai/gpt-5.2", "name": "GPT-5.2", "cost": 20},
                {"id": "openai/gpt-5-mini", "name": "GPT-5 Mini", "cost": 5},
                {"id": "openai/gpt-5-nano", "name": "GPT-5 Nano", "cost": 1},
                {"id": "openai/gpt-4.1", "name": "GPT-4.1", "cost": 10},
                {"id": "openai/gpt-4.1-mini", "name": "GPT-4.1 Mini", "cost": 4},
                {"id": "openai/gpt-4o", "name": "GPT-4o", "cost": 5},
                {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "cost": 1},
                {"id": "openai/o3-mini", "name": "OpenAI o3-mini", "cost": 3},
                {"id": "openai/o1", "name": "OpenAI o1", "cost": 8},
                {"id": "openai/gpt-oss-120b", "name": "GPT- OSS 120B", "cost": 2},
                {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B", "cost": 1},
            ]
        },
        "anthropic": {
            "models": [
                {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "cost": 8},
                {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "cost": 6},
                {"id": "anthropic/claude-opus-4.5", "name": "Claude Opus 4.5", "cost": 20},
                {"id": "anthropic/claude-haiku-4.5", "name": "Claude Haiku 4.5", "cost": 2},
                {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "cost": 5},
                {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "cost": 15},
                {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "cost": 1},
            ]
        },
        "google": {
            "models": [
                {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "cost": 5},
                {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "cost": 2},
                {"id": "google/gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "cost": 1},
                {"id": "google/gemini-2.5-flash-lite-preview-09-2025", "name": "Gemini 2.5 Flash Lite Preview", "cost": 1},
                {"id": "google/gemini-3-pro-preview", "name": "Gemini 3 Pro Preview", "cost": 8},
                {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash Preview", "cost": 3},
                {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "cost": 1},
            ]
        },
        "deepseek": {
            "models": [
                {"id": "deepseek/deepseek-v3.2", "name": "DeepSeek V3.2", "cost": 3},
                {"id": "deepseek/deepseek-chat-v3.1", "name": "DeepSeek Chat V3.1", "cost": 2},
                {"id": "deepseek/deepseek-chat-v3-0324", "name": "DeepSeek Chat V3 0324", "cost": 2},
                {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "cost": 2},
            ]
        },
        "meta": {
            "models": [
                {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "cost": 1},
            ]
        },
        "xai": {
            "models": [
                {"id": "x-ai/grok-4.1-fast", "name": "Grok 4.1 Fast", "cost": 5},
                {"id": "x-ai/grok-4-fast", "name": "Grok 4 Fast", "cost": 4},
                {"id": "x-ai/grok-code-fast-1", "name": "Grok Code Fast 1", "cost": 3},
            ]
        },
        "qwen": {
            "models": [
                {"id": "qwen/qwen3-coder", "name": "Qwen3 Coder", "cost": 2},
                {"id": "qwen/qwen3-235b-a22b-2507", "name": "Qwen3 235B A22B", "cost": 3},
            ]
        },
        "moonshotai": {
            "models": [
                {"id": "moonshotai/kimi-k2-0905", "name": "Kimi K2 0905", "cost": 3},
            ]
        },
        "mistral": {
            "models": [
                {"id": "mistralai/mistral-nemo", "name": "Mistral Nemo", "cost": 2},
            ]
        },
        "tngtech": {
            "models": [
                {"id": "tngtech/deepseek-r1t2-chimera:free", "name": "DeepSeek R1T2 Chimera (Free)", "cost": 0},
            ]
        },
    },

    "gen_image": {
        "flux": {
            "models": [
                {"id": "black-forest-labs/flux.2-pro", "name": "Flux 2.0 Pro", "cost": 4},
                {"id": "black-forest-labs/flux.2-max", "name": "Flux 2.0 Max", "cost": 4},
                {"id": "black-forest-labs/flux.2-flex", "name": "Flux 2.0 Flex", "cost": 2},
                {"id": "black-forest-labs/flux.2-klein-4b", "name": "Flux 2.0 Klein", "cost": 1},
                {"id": "fal-ai/stable-diffusion-v35-large", "name": "Stable Diffusion v3.5 Large", "cost": 3},
            ]
        },
        "riverflow": {
            "models": [
                {"id": "sourceful/riverflow-v2-max-preview", "name": "Riverflow v2 Max", "cost": 4},
                {"id": "sourceful/riverflow-v2-standard-preview", "name": "Riverflow v2 Standard", "cost": 2},
                {"id": "sourceful/riverflow-v2-fast-preview", "name": "Riverflow v2 Fast", "cost": 1},
            ]
        },
        "seedream": {
            "models": [
                {"id": "bytedance-seed/seedream-4.5", "name": "Seedream 4.5", "cost": 3},
            ]
        },
        "gemini_image": {
            "models": [
                {"id": "openai/gpt-5-image", "name": "GPT-5 Image", "cost": 5},
                {"id": "openai/gpt-5-image-mini", "name": "GPT-5 Image Mini", "cost": 2},
            ]
        },
    },

    "gen_nano_banana": {
        "nano_banana": {
            "models": [
                {"id": "google/gemini-3.1-flash-image-preview", "name": "Nano Banana 2", "cost": 10},
                {"id": "google/gemini-3-pro-image-preview", "name": "Nano Banana Pro", "cost": 8},
                {"id": "google/gemini-2.5-flash-image", "name": "Nano Banana", "cost": 3},
            ]
        },
    },

    "gen_video": {
        "kling": {
            "models": [
                {"id": "fal-ai/kling-video/v2.6/pro/text-to-video", "name": "Kling 2.6 Pro (Text)", "cost": 35},
                {"id": "fal-ai/kling-video/v2.6/pro/image-to-video", "name": "Kling 2.6 Pro (Img2Vid)", "cost": 35},
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
    },

    "gen_search": {
        "perplexity": {
            "models": [
                {"id": "perplexity/sonar-pro-search", "name": "Sonar Pro Search", "cost": 5},
                {"id": "perplexity/sonar-pro", "name": "Sonar Pro", "cost": 4},
                {"id": "perplexity/sonar-deep-research", "name": "Sonar Deep Research", "cost": 6},
                {"id": "perplexity/sonar-reasoning-pro", "name": "Sonar Reasoning Pro", "cost": 5},
                {"id": "perplexity/sonar-reasoning", "name": "Sonar Reasoning", "cost": 2},
                {"id": "perplexity/sonar", "name": "Sonar", "cost": 1},
                {"id": "perplexity/r1-1776", "name": "R1 1776", "cost": 3},
                {"id": "perplexity/llama-3.1-sonar-large-128k-online", "name": "Llama 3.1 Sonar Large 128k", "cost": 2},
                {"id": "perplexity/llama-3.1-sonar-small-128k-online", "name": "Llama 3.1 Sonar Small 128k", "cost": 1},
                {"id": "perplexity/llama-3-sonar-large-32k-chat", "name": "Llama 3 Sonar Large 32k Chat", "cost": 2},
                {"id": "perplexity/llama-3-sonar-small-32k-online", "name": "Llama 3 Sonar Small 32k Online", "cost": 1},
                {"id": "perplexity/llama-3-sonar-small-32k-chat", "name": "Llama 3 Sonar Small 32k Chat", "cost": 1},
                {"id": "perplexity/llama-3-sonar-large-32k-online", "name": "Llama 3 Sonar Large 32k Online", "cost": 2},
            ]
        }
    }
}
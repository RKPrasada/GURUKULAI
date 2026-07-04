import logging
import os

import httpx

logger = logging.getLogger(__name__)

_OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"

# Models tried in order — first available wins.
_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-26b-a4b-it:free",
    "openai/gpt-oss-20b:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
]


def call_gemini(prompt: str, system: str = "", timeout: float = 60.0) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set")
        return ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://gurukul-ai.app",
        "X-Title": "Gurukul AI",
    }

    for model in _MODELS:
        try:
            response = httpx.post(
                _OPENROUTER_BASE,
                headers=headers,
                json={"model": model, "messages": messages},
                timeout=timeout,
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            logger.warning(f"OpenRouter {model} returned {response.status_code}, trying next")
        except Exception as e:
            logger.warning(f"OpenRouter {model} failed: {e}, trying next")

    logger.error("All OpenRouter models failed")
    return ""

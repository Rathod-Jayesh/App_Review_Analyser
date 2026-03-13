from __future__ import annotations

from groq import Groq

from src.common.constants import settings

MODEL_HIGH_QUALITY = "llama-3.3-70b-versatile"
MODEL_FAST = "llama-3.1-8b-instant"

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def call_groq(
    system_prompt: str,
    user_prompt: str,
    model: str = MODEL_HIGH_QUALITY,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """Send a chat completion request to Groq and return the text response."""
    client = _get_client()

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    completion = client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content or ""

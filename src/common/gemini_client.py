from __future__ import annotations

import json

import google.generativeai as genai

from src.common.constants import settings

GEMINI_MODEL = "gemini-2.5-flash"

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True


def call_gemini(
    system_prompt: str,
    user_prompt: str,
    model: str = GEMINI_MODEL,
    temperature: float = 0.4,
    max_tokens: int = 8192,
    json_mode: bool = False,
) -> str:
    """Send a request to Gemini and return the text response."""
    _ensure_configured()

    generation_config: dict = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if json_mode:
        generation_config["response_mime_type"] = "application/json"

    model_instance = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt,
        generation_config=generation_config,
    )

    response = model_instance.generate_content(user_prompt)
    return response.text or ""

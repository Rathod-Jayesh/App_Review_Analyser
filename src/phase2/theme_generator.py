from __future__ import annotations

import json
import logging
import random
from datetime import datetime

from src.common.models import Review, Theme, ThemeStore
from src.common.gemini_client import call_gemini
from src.common.constants import DATA_DIR, THEMES_FILE

logger = logging.getLogger(__name__)

THEME_SYSTEM_PROMPT = """You are an expert product analyst specializing in fintech apps.
You will analyze user reviews for GROWW, a popular Indian stock trading
and mutual fund investment app.

Your task: Identify exactly 3 to 5 recurring themes from the reviews.
Themes should be specific and actionable (not generic like "good app" or "bad app").

RULES:
- Each theme must have a short id (snake_case), a human-readable name, and a description
- Themes should cover the majority of reviews
- Focus on product-relevant themes (UX issues, feature requests, bugs, praise areas)
- Return valid JSON only"""


def _build_user_prompt(reviews: list[Review]) -> str:
    review_lines = "\n".join(
        f"[{r.rating}*] {r.text}" for r in reviews
    )
    return f"""Analyze these {len(reviews)} user reviews and identify 3-5 recurring themes.

Reviews:
{review_lines}

Return JSON in this exact format:
{{
  "themes": [
    {{
      "id": "snake_case_id",
      "name": "Human Readable Name",
      "description": "What this theme covers"
    }}
  ]
}}"""


def _sample_reviews(reviews: list[Review], sample_size: int = 60) -> list[Review]:
    """Stratified sampling by rating — takes up to sample_size/5 per bucket."""
    by_rating: dict[int, list[Review]] = {1: [], 2: [], 3: [], 4: [], 5: []}

    for r in reviews:
        bucket = by_rating.get(r.rating)
        if bucket is not None:
            bucket.append(r)

    per_bucket = max(1, sample_size // 5)
    sampled: list[Review] = []

    for rating in range(1, 6):
        bucket = by_rating[rating]
        random.shuffle(bucket)
        sampled.extend(bucket[:per_bucket])

    return sampled


def generate_themes(reviews: list[Review]) -> ThemeStore:
    """Discover 3-5 themes from a representative sample using Gemini."""
    if not reviews:
        raise ValueError("No reviews available for theme discovery")

    sampled = _sample_reviews(reviews, sample_size=60)
    logger.info("Sampled %d reviews (from %d total) for theme discovery via Gemini", len(sampled), len(reviews))

    prompt = _build_user_prompt(sampled)
    raw = call_gemini(
        system_prompt=THEME_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0.3,
        json_mode=True,
    )

    parsed = json.loads(raw)
    final_themes_raw = parsed.get("themes", [])

    themes = [
        Theme(id=t["id"], name=t["name"], description=t["description"])
        for t in final_themes_raw
    ]

    store = ThemeStore(
        generated_at=datetime.now().isoformat(),
        review_count_used=len(reviews),
        themes=themes,
    )

    _save_themes(store)
    return store


def _save_themes(store: ThemeStore) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    THEMES_FILE.write_text(
        json.dumps(store.model_dump(), indent=2),
        encoding="utf-8",
    )


def load_themes() -> ThemeStore | None:
    if not THEMES_FILE.exists():
        return None
    try:
        raw = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
        return ThemeStore(**raw)
    except (json.JSONDecodeError, Exception):
        return None

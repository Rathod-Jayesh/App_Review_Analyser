from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime

from src.common.models import Review, Theme, ThemeStore
from src.common.groq_client import call_groq, MODEL_HIGH_QUALITY
from src.common.constants import DATA_DIR, THEMES_FILE

logger = logging.getLogger(__name__)

BATCH_SYSTEM_PROMPT = """You are an expert product analyst specializing in fintech apps.
You will analyze user reviews for GROWW, a popular Indian stock trading
and mutual fund investment app.

Your task: Identify exactly 3 to 5 recurring themes from the reviews.
Themes should be specific and actionable (not generic like "good app" or "bad app").

RULES:
- Each theme must have a short id (snake_case), a human-readable name, and a description
- Themes should cover the majority of reviews
- Focus on product-relevant themes (UX issues, feature requests, bugs, praise areas)
- Return valid JSON only"""

MERGE_SYSTEM_PROMPT = """You are an expert product analyst specializing in fintech apps.
You will receive multiple sets of themes extracted from different batches of user reviews
for GROWW, a popular Indian stock trading and mutual fund investment app.

Your task: Merge and consolidate all these themes into exactly 3 to 5 final themes.

RULES:
- Combine similar or overlapping themes into one
- Each final theme must have a short id (snake_case), a human-readable name, and a description
- Focus on product-relevant themes (UX issues, feature requests, bugs, praise areas)
- The final themes should represent the most important patterns across ALL batches
- Return valid JSON only"""

TOKENS_PER_BATCH = 8000


def _estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.4)


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


def _build_merge_prompt(batch_themes: list[list[dict]]) -> str:
    sections = []
    for i, themes in enumerate(batch_themes, 1):
        lines = "\n".join(
            f"  - {t['name']}: {t['description']}" for t in themes
        )
        sections.append(f"Batch {i}:\n{lines}")

    combined = "\n\n".join(sections)
    return f"""Consolidate these theme sets into 3-5 final themes:

{combined}

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


def _split_into_batches(reviews: list[Review]) -> list[list[Review]]:
    """Split reviews into batches that fit within the token limit."""
    prompt_overhead = _estimate_tokens(BATCH_SYSTEM_PROMPT) + 200
    max_review_tokens = TOKENS_PER_BATCH - prompt_overhead

    batches: list[list[Review]] = []
    current_batch: list[Review] = []
    current_tokens = 0

    for r in reviews:
        line = f"[{r.rating}*] {r.text}"
        line_tokens = _estimate_tokens(line)

        if current_tokens + line_tokens > max_review_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(r)
        current_tokens += line_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def sample_reviews(reviews: list[Review], sample_size: int = 80) -> list[Review]:
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


def _call_with_retry(
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 5,
) -> str:
    """Call Groq with automatic retry + backoff on rate-limit errors."""
    for attempt in range(max_retries):
        try:
            return call_groq(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=MODEL_HIGH_QUALITY,
                temperature=0.3,
                json_mode=True,
            )
        except Exception as exc:
            if "rate_limit" in str(exc).lower() or "413" in str(exc):
                wait = 90 * (attempt + 1)
                logger.info("Rate limited — waiting %ds before retry %d/%d", wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Groq rate limit exceeded after all retries")


def _extract_themes_from_batch(reviews: list[Review]) -> list[dict]:
    prompt = _build_user_prompt(reviews)
    raw = _call_with_retry(BATCH_SYSTEM_PROMPT, prompt)
    parsed = json.loads(raw)
    return parsed.get("themes", [])


def generate_themes(reviews: list[Review]) -> ThemeStore:
    """
    Use a stratified sample of reviews to discover 3-5 themes quickly.
    Sampling keeps it to a single LLM call instead of many batches.
    """
    if not reviews:
        raise ValueError("No reviews available for theme discovery")

    sampled = sample_reviews(reviews, sample_size=100)
    logger.info("Sampled %d reviews (from %d total) for theme discovery", len(sampled), len(reviews))

    final_themes_raw = _extract_themes_from_batch(sampled)

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

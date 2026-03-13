from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import datetime

from src.common.constants import DATA_DIR, CLASSIFICATIONS_FILE
from src.common.groq_client import call_groq, MODEL_FAST
from src.common.models import (
    ClassificationStore,
    ClassifiedReview,
    Review,
    Theme,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 25

CLASSIFICATION_SYSTEM_PROMPT = """You are a review classifier for GROWW app reviews.
You will be given a set of themes and a batch of reviews.
Classify each review into exactly ONE theme.

RULES:
- Every review MUST be assigned to a theme
- If a review could fit multiple themes, pick the most dominant one
- confidence should be between 0.0 and 1.0
- Return valid JSON only"""


def _build_classification_prompt(
    themes: list[Theme],
    batch: list[Review],
) -> str:
    theme_lines = "\n".join(
        f"- {t.id}: {t.name} — {t.description}" for t in themes
    )
    review_lines = "\n".join(
        f"[{r.id}] ({r.rating}★) {r.text}" for r in batch
    )
    return f"""THEMES:
{theme_lines}

REVIEWS:
{review_lines}

Classify each review. Return JSON:
{{
  "classifications": [
    {{ "reviewId": "review_id_here", "themeId": "theme_id_here", "confidence": 0.95 }}
  ]
}}"""


def _classify_batch_with_retry(
    themes: list[Theme],
    batch: list[Review],
    max_retries: int = 3,
) -> list[ClassifiedReview]:
    prompt = _build_classification_prompt(themes, batch)

    for attempt in range(max_retries):
        try:
            raw = call_groq(
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=prompt,
                model=MODEL_FAST,
                temperature=0.1,
                json_mode=True,
            )
            parsed = json.loads(raw)
            raw_classifications = parsed.get("classifications", [])

            valid_theme_ids = {t.id for t in themes}
            batch_review_ids = {r.id for r in batch}

            results: list[ClassifiedReview] = []
            for c in raw_classifications:
                review_id = c.get("reviewId", "")
                theme_id = c.get("themeId", "")
                confidence = float(c.get("confidence", 0.0))

                if review_id not in batch_review_ids:
                    continue
                if theme_id not in valid_theme_ids:
                    theme_id = themes[0].id
                    confidence = min(confidence, 0.5)

                results.append(
                    ClassifiedReview(
                        review_id=review_id,
                        theme_id=theme_id,
                        confidence=round(confidence, 2),
                    )
                )

            classified_ids = {r.review_id for r in results}
            for r in batch:
                if r.id not in classified_ids:
                    results.append(
                        ClassifiedReview(
                            review_id=r.id,
                            theme_id=themes[0].id,
                            confidence=0.3,
                        )
                    )

            return results

        except Exception as exc:
            if "rate_limit" in str(exc).lower() or "413" in str(exc):
                wait = 65 * (attempt + 1)
                logger.info("Rate limited — waiting %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("Classification failed after all retries")


def classify_all_reviews(
    themes: list[Theme],
    reviews: list[Review],
) -> ClassificationStore:
    """Classify every review into one theme using batched LLM calls."""
    if not themes:
        raise ValueError("No themes found. Run Phase 2a first.")
    if not reviews:
        raise ValueError("No reviews found. Run Phase 1 first.")

    all_classifications: list[ClassifiedReview] = []
    total_batches = (len(reviews) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(reviews), BATCH_SIZE):
        batch = reviews[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        logger.info(
            "Classifying batch %d/%d (%d reviews)",
            batch_num,
            total_batches,
            len(batch),
        )

        results = _classify_batch_with_retry(themes, batch)
        all_classifications.extend(results)

        if i + BATCH_SIZE < len(reviews):
            time.sleep(8)

    distribution = dict(Counter(c.theme_id for c in all_classifications))

    store = ClassificationStore(
        classified_at=datetime.now().isoformat(),
        total_classified=len(all_classifications),
        theme_distribution=distribution,
        classifications=all_classifications,
    )

    _save_classifications(store)
    return store


def _save_classifications(store: ClassificationStore) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CLASSIFICATIONS_FILE.write_text(
        json.dumps(store.model_dump(), indent=2),
        encoding="utf-8",
    )


def load_classifications() -> ClassificationStore | None:
    if not CLASSIFICATIONS_FILE.exists():
        return None
    try:
        raw = json.loads(CLASSIFICATIONS_FILE.read_text(encoding="utf-8"))
        return ClassificationStore(**raw)
    except (json.JSONDecodeError, Exception):
        return None

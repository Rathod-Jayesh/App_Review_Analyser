from __future__ import annotations

from datetime import datetime

from langdetect import detect_langs, LangDetectException, DetectorFactory

from src.common.models import Review
from src.common.pii_scrubber import scrub_pii

DetectorFactory.seed = 0
MIN_WORD_COUNT = 5
EN_CONFIDENCE_THRESHOLD = 0.8


def _parse_date(date_str: str) -> datetime:
    """Best-effort ISO date parse."""
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return datetime.now()


def _has_enough_words(text: str) -> bool:
    return len(text.split()) >= MIN_WORD_COUNT


def _is_english(text: str) -> bool:
    """Return True only if English confidence >= 80%."""
    if not text or len(text.strip()) < 3:
        return False
    try:
        langs = detect_langs(text)
        for lang in langs:
            if lang.lang == "en" and lang.prob >= EN_CONFIDENCE_THRESHOLD:
                return True
        return False
    except LangDetectException:
        return False


def _normalize_review(raw: dict, prefix: str) -> Review:
    dt = _parse_date(raw.get("date", ""))
    text = scrub_pii(raw.get("text", ""))
    return Review(
        id=f"{prefix}_{raw.get('id', '')}",
        rating=int(raw.get("score", 0)),
        text=text,
        date=dt.isoformat(),
    )


def normalize_reviews(
    play_store_raw: list[dict],
    app_store_raw: list[dict],
) -> list[Review]:
    """
    Merge and normalize raw reviews from both stores.
    Filters out:
      - Reviews with fewer than 5 words
      - Non-English reviews
    PII is scrubbed and stored directly in the text field.
    Deduplicates and sorts newest-first.
    """
    reviews: list[Review] = []

    for r in play_store_raw:
        text = r.get("text", "")
        if not _has_enough_words(text):
            continue
        if not _is_english(text):
            continue
        reviews.append(_normalize_review(r, "ps"))

    for r in app_store_raw:
        text = r.get("text", "")
        if not _has_enough_words(text):
            continue
        if not _is_english(text):
            continue
        reviews.append(_normalize_review(r, "as"))

    reviews.sort(key=lambda r: r.date, reverse=True)

    seen: set[str] = set()
    unique: list[Review] = []
    for review in reviews:
        if review.id not in seen:
            seen.add(review.id)
            unique.append(review)

    return unique

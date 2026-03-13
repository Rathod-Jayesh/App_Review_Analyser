from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from src.common.models import Review, ReviewStore
from src.common.constants import DATA_DIR, REVIEWS_FILE


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "weekly-notes").mkdir(parents=True, exist_ok=True)


def save_reviews(reviews: list[Review]) -> None:
    """Persist the full review list to data/reviews.json."""
    _ensure_data_dir()

    store = ReviewStore(
        last_fetched=datetime.now().isoformat(),
        total_count=len(reviews),
        reviews=reviews,
    )

    REVIEWS_FILE.write_text(
        json.dumps(store.model_dump(), indent=2, default=str),
        encoding="utf-8",
    )


def load_reviews() -> Optional[ReviewStore]:
    """Load the review store from disk. Returns None if file missing."""
    _ensure_data_dir()

    if not REVIEWS_FILE.exists():
        return None

    try:
        raw = json.loads(REVIEWS_FILE.read_text(encoding="utf-8"))
        return ReviewStore(**raw)
    except (json.JSONDecodeError, Exception):
        return None


def get_filtered_reviews(
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
) -> list[Review]:
    """Return reviews matching the given filters."""
    store = load_reviews()
    if not store:
        return []

    results = store.reviews

    if min_rating is not None:
        results = [r for r in results if r.rating >= min_rating]

    if max_rating is not None:
        results = [r for r in results if r.rating <= max_rating]

    return results

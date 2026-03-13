from __future__ import annotations

from datetime import datetime

from google_play_scraper import Sort, reviews

from src.common.constants import settings
from src.common.date_helpers import get_cutoff_date


def fetch_play_store_reviews(weeks: int | None = None, max_reviews: int | None = None) -> list[dict]:
    """
    Fetch recent reviews from the Google Play Store for GROWW.

    Returns a list of raw review dicts. Paginates until it hits the
    date cutoff or the max_reviews cap.
    """
    weeks = weeks or settings.review_weeks
    cutoff = get_cutoff_date(weeks)
    cap = max_reviews or settings.max_reviews_per_source

    all_reviews: list[dict] = []
    continuation_token = None

    while len(all_reviews) < cap:
        batch_size = min(200, cap - len(all_reviews))

        result, continuation_token = reviews(
            settings.play_store_app_id,
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=continuation_token,
        )

        if not result:
            break

        for r in result:
            review_date = r.get("at")
            if isinstance(review_date, datetime) and review_date < cutoff:
                return all_reviews[:cap]

            all_reviews.append({
                "id": r.get("reviewId", str(len(all_reviews))),
                "user_name": r.get("userName", "Anonymous"),
                "score": r.get("score", 0),
                "text": r.get("content", ""),
                "date": (
                    review_date.isoformat()
                    if isinstance(review_date, datetime)
                    else str(review_date)
                ),
                "version": r.get("reviewCreatedVersion"),
                "thumbs_up": r.get("thumbsUpCount", 0),
            })

        if not continuation_token:
            break

    return all_reviews[:cap]

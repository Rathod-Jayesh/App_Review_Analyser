from __future__ import annotations

from datetime import datetime

import requests

from src.common.constants import settings
from src.common.date_helpers import get_cutoff_date

ITUNES_RSS_URL = (
    "https://itunes.apple.com/{country}/rss/customerreviews"
    "/id={app_id}/sortBy=mostRecent/page={page}/json"
)
MAX_PAGES = 10


def _parse_itunes_date(date_str: str) -> datetime:
    """Parse the date format returned by iTunes RSS feed."""
    for fmt in ("%Y-%m-%dT%H:%M:%S-07:00", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.now()


def fetch_app_store_reviews(weeks: int | None = None) -> list[dict]:
    """
    Fetch recent reviews from the Apple App Store for GROWW
    using the public iTunes RSS feed.
    """
    weeks = weeks or settings.review_weeks
    cutoff = get_cutoff_date(weeks)
    cap = settings.max_reviews_per_source

    all_reviews: list[dict] = []

    for page in range(1, MAX_PAGES + 1):
        if len(all_reviews) >= cap:
            break

        url = ITUNES_RSS_URL.format(
            country="in",
            app_id=settings.app_store_app_id,
            page=page,
        )

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"App Store page {page} fetch error: {exc}")
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break

        review_entries = [e for e in entries if "im:rating" in e]
        if not review_entries:
            break

        hit_cutoff = False
        for entry in review_entries:
            review_date = _parse_itunes_date(
                entry.get("updated", {}).get("label", "")
            )
            if review_date.replace(tzinfo=None) < cutoff:
                hit_cutoff = True
                continue

            all_reviews.append({
                "id": entry.get("id", {}).get("label", str(len(all_reviews))),
                "user_name": entry.get("author", {}).get("name", {}).get("label", "Anonymous"),
                "score": int(entry.get("im:rating", {}).get("label", "0")),
                "text": entry.get("content", {}).get("label", ""),
                "date": review_date.isoformat(),
                "version": entry.get("im:version", {}).get("label"),
            })

            if len(all_reviews) >= cap:
                break

        if hit_cutoff:
            break

    return all_reviews[:cap]

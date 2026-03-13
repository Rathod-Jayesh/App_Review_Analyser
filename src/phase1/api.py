from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from src.common.models import FetchConfig, ReviewSource
from src.phase1.play_store_scraper import fetch_play_store_reviews
from src.phase1.app_store_scraper import fetch_app_store_reviews
from src.phase1.review_normalizer import normalize_reviews
from src.common.storage import save_reviews, load_reviews, get_filtered_reviews

router = APIRouter(prefix="/api/reviews", tags=["Phase 1 - Reviews"])


@router.post("/fetch")
def handle_fetch_reviews(config: Optional[FetchConfig] = None):
    """
    Scrape reviews from Play Store and/or App Store,
    normalize, filter (English-only, 5+ words), scrub PII, and save.
    """
    cfg = config or FetchConfig()
    errors: list[str] = []

    play_store_raw: list[dict] = []
    app_store_raw: list[dict] = []

    if ReviewSource.PLAY_STORE in cfg.sources:
        try:
            play_store_raw = fetch_play_store_reviews(cfg.weeks, cfg.max_reviews)
        except Exception as exc:
            errors.append(f"Play Store: {exc}")

    if ReviewSource.APP_STORE in cfg.sources:
        try:
            app_store_raw = fetch_app_store_reviews(cfg.weeks)
        except Exception as exc:
            errors.append(f"App Store: {exc}")

    if not play_store_raw and not app_store_raw:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "No reviews fetched from any source",
                "details": errors,
            },
        )

    normalized = normalize_reviews(play_store_raw, app_store_raw)
    save_reviews(normalized)

    raw_total = len(play_store_raw) + len(app_store_raw)
    filtered_out = raw_total - len(normalized)

    dates = [r.date for r in normalized]
    return {
        "success": True,
        "data": {
            "total_count": len(normalized),
            "raw_fetched": raw_total,
            "filtered_out": filtered_out,
            "date_range": {
                "from": min(dates) if dates else None,
                "to": max(dates) if dates else None,
            },
        },
        "warnings": errors if errors else None,
    }


@router.get("/stats")
def handle_get_review_stats():
    """Lightweight stats: counts and rating distribution without sending all reviews."""
    store = load_reviews()
    if not store or not store.reviews:
        return {
            "success": True,
            "data": {
                "total_count": 0,
                "average_rating": 0,
                "last_fetched": None,
                "rating_distribution": {str(i): 0 for i in range(1, 6)},
            },
        }

    ratings = [r.rating for r in store.reviews]
    dist = {str(i): ratings.count(i) for i in range(1, 6)}
    dates = [r.date for r in store.reviews]

    return {
        "success": True,
        "data": {
            "total_count": len(store.reviews),
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "last_fetched": store.last_fetched,
            "rating_distribution": dist,
            "date_range": {
                "from": min(dates) if dates else None,
                "to": max(dates) if dates else None,
            },
        },
    }


@router.get("")
def handle_get_reviews(
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
):
    """
    Return stored reviews, optionally filtered by rating.
    """
    has_filters = any(v is not None for v in [min_rating, max_rating])

    if has_filters:
        filtered = get_filtered_reviews(
            min_rating=min_rating,
            max_rating=max_rating,
        )
        return {
            "success": True,
            "data": {
                "total_count": len(filtered),
                "reviews": [r.model_dump() for r in filtered],
            },
        }

    store = load_reviews()
    if not store:
        return {
            "success": True,
            "data": {
                "last_fetched": None,
                "total_count": 0,
                "average_rating": 0,
                "reviews": [],
            },
        }

    avg = round(sum(r.rating for r in store.reviews) / len(store.reviews), 2) if store.reviews else 0
    data = store.model_dump()
    data["average_rating"] = avg
    return {"success": True, "data": data}

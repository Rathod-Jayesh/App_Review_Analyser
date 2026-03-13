from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.common.storage import load_reviews
from src.phase2.theme_generator import generate_themes, load_themes
from src.phase2.review_classifier import classify_all_reviews, load_classifications

router = APIRouter(prefix="/api/themes", tags=["Phase 2 - Themes"])


# ─── Phase 2a: Theme Discovery ───


@router.post("/generate")
def handle_generate_themes():
    """
    Discover 3-5 themes from ALL stored reviews using Groq LLM.
    Reviews are split into batches to respect Groq rate limits,
    then themes are merged into a final consolidated set.
    """
    store = load_reviews()
    if not store or not store.reviews:
        raise HTTPException(
            status_code=400,
            detail="No reviews found. Run Phase 1 (POST /api/reviews/fetch) first.",
        )

    try:
        theme_store = generate_themes(store.reviews)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "success": True,
        "data": {
            "generated_at": theme_store.generated_at,
            "review_count_used": theme_store.review_count_used,
            "theme_count": len(theme_store.themes),
            "themes": [t.model_dump() for t in theme_store.themes],
        },
    }


@router.get("")
def handle_get_themes():
    """Return previously generated themes."""
    theme_store = load_themes()
    if not theme_store:
        return {
            "success": True,
            "data": {
                "generated_at": None,
                "theme_count": 0,
                "themes": [],
            },
        }

    return {
        "success": True,
        "data": {
            "generated_at": theme_store.generated_at,
            "review_count_used": theme_store.review_count_used,
            "theme_count": len(theme_store.themes),
            "themes": [t.model_dump() for t in theme_store.themes],
        },
    }


# ─── Phase 2b: Review Classification ───


@router.post("/classify")
def handle_classify_reviews():
    """
    Classify ALL stored reviews into discovered themes using Groq LLM.
    Reviews are processed in batches of 25 with the fast model.
    """
    review_store = load_reviews()
    if not review_store or not review_store.reviews:
        raise HTTPException(
            status_code=400,
            detail="No reviews found. Run Phase 1 first.",
        )

    theme_store = load_themes()
    if not theme_store or not theme_store.themes:
        raise HTTPException(
            status_code=400,
            detail="No themes found. Run Phase 2a (POST /api/themes/generate) first.",
        )

    try:
        classification_store = classify_all_reviews(
            themes=theme_store.themes,
            reviews=review_store.reviews,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "success": True,
        "data": {
            "classified_at": classification_store.classified_at,
            "total_classified": classification_store.total_classified,
            "theme_distribution": classification_store.theme_distribution,
        },
    }


@router.get("/classifications")
def handle_get_classifications():
    """Return previously generated classifications with theme distribution."""
    classification_store = load_classifications()
    if not classification_store:
        return {
            "success": True,
            "data": {
                "classified_at": None,
                "total_classified": 0,
                "theme_distribution": {},
                "classifications": [],
            },
        }

    return {
        "success": True,
        "data": {
            "classified_at": classification_store.classified_at,
            "total_classified": classification_store.total_classified,
            "theme_distribution": classification_store.theme_distribution,
            "classifications": [
                c.model_dump() for c in classification_store.classifications
            ],
        },
    }

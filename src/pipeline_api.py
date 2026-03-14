"""
Single run-all endpoint for Vercel serverless.
Runs the entire pipeline in one function invocation so /tmp is shared
across all phases.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.common.models import FetchConfig, ReviewSource
from src.phase1.play_store_scraper import fetch_play_store_reviews
from src.phase1.review_normalizer import normalize_reviews
from src.common.storage import save_reviews
from src.phase2.theme_generator import generate_themes
from src.phase2.review_classifier import classify_all_reviews
from src.phase3.data_aggregator import aggregate_data
from src.phase3.note_generator import generate_pulse_note

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


class PipelineConfig(BaseModel):
    weeks: int = Field(default=8, ge=1, le=52)
    max_reviews: int = Field(default=1000, ge=100, le=5000)


@router.post("/run-all")
def handle_run_all(config: Optional[PipelineConfig] = None):
    """
    Run the full pipeline in a single request:
    Fetch → Themes → Classify → Generate Note.
    Designed for serverless where /tmp is only shared within one invocation.
    """
    cfg = config or PipelineConfig()
    steps_completed: list[str] = []
    result_data: dict = {}

    try:
        raw_reviews = fetch_play_store_reviews(cfg.weeks, cfg.max_reviews)
        if not raw_reviews:
            raise HTTPException(status_code=500, detail="No reviews fetched from Play Store.")

        normalized = normalize_reviews(raw_reviews, [])
        save_reviews(normalized)

        result_data["fetch"] = {
            "total_count": len(normalized),
            "raw_fetched": len(raw_reviews),
            "filtered_out": len(raw_reviews) - len(normalized),
        }
        steps_completed.append("fetch")
        logger.info("Phase 1 done: %d reviews", len(normalized))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fetch failed: {exc}")

    try:
        theme_store = generate_themes(normalized)
        result_data["themes"] = {
            "theme_count": len(theme_store.themes),
            "themes": [t.model_dump() for t in theme_store.themes],
        }
        steps_completed.append("themes")
        logger.info("Phase 2a done: %d themes", len(theme_store.themes))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Theme generation failed: {exc}. Completed: {steps_completed}",
        )

    try:
        classification_store = classify_all_reviews(
            themes=theme_store.themes,
            reviews=normalized,
        )
        result_data["classify"] = {
            "total_classified": classification_store.total_classified,
            "theme_distribution": classification_store.theme_distribution,
        }
        steps_completed.append("classify")
        logger.info("Phase 2b done: %d classified", classification_store.total_classified)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {exc}. Completed: {steps_completed}",
        )

    try:
        report_date = datetime.now().strftime("%Y-%m-%d")
        aggregation = aggregate_data(
            reviews=normalized,
            themes=theme_store.themes,
            classifications=classification_store.classifications,
            report_date=report_date,
            weeks=cfg.weeks,
        )
        note = generate_pulse_note(aggregation)
        result_data["note"] = {
            "report_date": note.report_date,
            "period": f"{note.period_start} to {note.period_end}",
            "total_reviews": note.total_reviews,
            "average_rating": note.average_rating,
            "generated_at": note.generated_at,
            "markdown_content": note.markdown_content,
            "plaintext_content": note.plaintext_content,
        }
        steps_completed.append("generate")
        logger.info("Phase 3 done: pulse for %s", note.report_date)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Note generation failed: {exc}. Completed: {steps_completed}",
        )

    return {
        "success": True,
        "steps_completed": steps_completed,
        "data": result_data,
    }

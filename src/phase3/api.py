from __future__ import annotations

import io
from datetime import datetime

import markdown as md_lib
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.common.constants import WEEKLY_NOTES_DIR
from src.common.storage import load_reviews
from src.phase2.theme_generator import load_themes
from src.phase2.review_classifier import load_classifications
from src.phase3.data_aggregator import aggregate_data
from src.phase3.note_generator import (
    generate_pulse_note,
    load_latest_note,
    load_note,
    list_note_dates,
)

router = APIRouter(prefix="/api/weekly-note", tags=["Phase 3 - Weekly Pulse Note"])


@router.post("/generate")
def handle_generate_note(
    report_date: str | None = Query(default=None),
    weeks: int = Query(default=12, ge=1, le=52),
):
    """
    Generate a weekly pulse note using Gemini.
    weeks: the configured fetch range so the report period is accurate.
    """
    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d")

    review_store = load_reviews()
    if not review_store or not review_store.reviews:
        raise HTTPException(status_code=400, detail="No reviews found. Run Phase 1 first.")

    theme_store = load_themes()
    if not theme_store or not theme_store.themes:
        raise HTTPException(status_code=400, detail="No themes found. Run Phase 2a first.")

    classification_store = load_classifications()
    if not classification_store or not classification_store.classifications:
        raise HTTPException(status_code=400, detail="No classifications found. Run Phase 2b first.")

    try:
        aggregation = aggregate_data(
            reviews=review_store.reviews,
            themes=theme_store.themes,
            classifications=classification_store.classifications,
            report_date=report_date,
            weeks=weeks,
        )
        note = generate_pulse_note(aggregation)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "success": True,
        "data": {
            "report_date": note.report_date,
            "period": f"{note.period_start} to {note.period_end}",
            "total_reviews": note.total_reviews,
            "average_rating": note.average_rating,
            "generated_at": note.generated_at,
            "files": {
                "markdown": note.md_file,
                "plaintext": note.txt_file,
            },
            "markdown_content": note.markdown_content,
        },
    }


@router.get("/latest")
def handle_get_latest_note():
    """Return the most recently generated pulse note."""
    note = load_latest_note()
    if not note:
        return {
            "success": True,
            "data": None,
            "message": "No pulse notes generated yet.",
        }

    return {
        "success": True,
        "data": {
            "report_date": note.report_date,
            "period": f"{note.period_start} to {note.period_end}",
            "total_reviews": note.total_reviews,
            "average_rating": note.average_rating,
            "generated_at": note.generated_at,
            "markdown_content": note.markdown_content,
            "plaintext_content": note.plaintext_content,
        },
    }


@router.get("/list")
def handle_list_notes():
    """Return a list of all generated pulse note dates."""
    dates = list_note_dates()
    return {"success": True, "data": dates}


@router.get("/download-pdf/{report_date}")
def handle_download_pdf(report_date: str):
    """Download the pulse note as a styled PDF."""
    note = load_note(report_date)
    if not note:
        raise HTTPException(status_code=404, detail=f"No pulse note for {report_date}.")

    html_body = md_lib.markdown(note.markdown_content, extensions=["extra"])
    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; color: #1f2937; font-size: 14px; line-height: 1.7; }}
  h1 {{ color: #00b386; font-size: 22px; border-bottom: 2px solid #e6faf5; padding-bottom: 8px; }}
  h2 {{ color: #374151; font-size: 16px; margin-top: 24px; }}
  blockquote {{ border-left: 3px solid #00d09c; padding: 8px 16px; background: #f0fdf8; font-style: italic; margin: 12px 0; border-radius: 0 6px 6px 0; }}
  li {{ margin-bottom: 6px; }}
  strong {{ color: #1f2937; }}
  p {{ margin-bottom: 8px; }}
</style></head><body>{html_body}</body></html>"""

    try:
        from xhtml2pdf import pisa
        pdf_buffer = io.BytesIO()
        pisa.CreatePDF(io.StringIO(full_html), dest=pdf_buffer)
        pdf_buffer.seek(0)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="pulse-{report_date}.pdf"'},
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="xhtml2pdf not installed. Run: pip install xhtml2pdf")


@router.get("/{report_date}")
def handle_get_note(report_date: str):
    """Return a specific pulse note by its report date (YYYY-MM-DD)."""
    note = load_note(report_date)
    if not note:
        raise HTTPException(
            status_code=404,
            detail=f"Pulse note for '{report_date}' not found.",
        )

    return {
        "success": True,
        "data": {
            "report_date": note.report_date,
            "period": f"{note.period_start} to {note.period_end}",
            "total_reviews": note.total_reviews,
            "average_rating": note.average_rating,
            "generated_at": note.generated_at,
            "markdown_content": note.markdown_content,
            "plaintext_content": note.plaintext_content,
        },
    }

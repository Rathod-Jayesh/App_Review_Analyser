from __future__ import annotations

import io
from datetime import datetime

import markdown as md_lib
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


def _build_pdf(content: str, report_date: str) -> io.BytesIO:
    """Build a styled PDF from markdown/plain text content."""
    from fpdf import FPDF
    import re

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    lines = content.split("\n")

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(0, 179, 134)
            pdf.cell(0, 10, stripped[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(0, 208, 156)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)
        elif stripped.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(55, 65, 81)
            pdf.cell(0, 8, stripped[3:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif stripped.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(75, 85, 99)
            pdf.cell(0, 7, stripped[4:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif stripped.startswith("> "):
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(55, 65, 81)
            clean = re.sub(r"[*_`]", "", stripped[2:])
            pdf.set_x(15)
            pdf.multi_cell(175, 5, f'"{clean}"')
            pdf.ln(2)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(31, 41, 55)
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped[2:])
            clean = re.sub(r"[*_`]", "", clean)
            pdf.set_x(15)
            pdf.multi_cell(175, 5, f"  {clean}")
            pdf.ln(1)
        elif re.match(r"^\d+\.\s", stripped):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(31, 41, 55)
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
            clean = re.sub(r"[*_`]", "", clean)
            pdf.set_x(15)
            pdf.multi_cell(175, 5, f"  {clean}")
            pdf.ln(1)
        elif stripped:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(75, 85, 99)
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
            clean = re.sub(r"[*_`]", "", clean)
            pdf.multi_cell(0, 5, clean)
            pdf.ln(2)
        else:
            pdf.ln(3)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer


@router.get("/download-pdf/{report_date}")
def handle_download_pdf(report_date: str):
    """Download the pulse note as a styled PDF (loads from disk)."""
    note = load_note(report_date)
    if not note:
        raise HTTPException(status_code=404, detail=f"No pulse note for {report_date}.")

    content = note.plaintext_content or note.markdown_content
    pdf_buffer = _build_pdf(content, report_date)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="pulse-{report_date}.pdf"'},
    )


class PdfRequest(BaseModel):
    markdown_content: str
    report_date: str = ""


@router.post("/download-pdf")
def handle_download_pdf_post(req: PdfRequest):
    """Generate PDF from provided content (works on serverless where disk is ephemeral)."""
    if not req.markdown_content:
        raise HTTPException(status_code=400, detail="No content provided.")

    date_label = req.report_date or datetime.now().strftime("%Y-%m-%d")
    pdf_buffer = _build_pdf(req.markdown_content, date_label)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="pulse-{date_label}.pdf"'},
    )


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

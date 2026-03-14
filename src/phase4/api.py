from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.common.constants import WEEKLY_NOTES_DIR
from src.common.models import PulseNote
from src.phase3.note_generator import load_latest_note, load_note
from src.phase4.email_composer import compose_email
from src.phase4.email_sender import save_draft_eml, send_email

router = APIRouter(prefix="/api/email", tags=["Phase 4 - Email"])


class DraftRequest(BaseModel):
    report_date: str | None = None
    recipient: str
    recipient_name: str | None = None


class SendRequest(BaseModel):
    report_date: str | None = None
    recipient: str
    recipient_name: str | None = None
    send: bool = False
    markdown_content: str | None = None
    plaintext_content: str | None = None


@router.post("/draft")
def handle_draft_email(body: DraftRequest):
    note = _resolve_note(body.report_date)

    draft = compose_email(
        note=note,
        recipient=body.recipient,
        recipient_name=body.recipient_name,
    )

    eml_path = save_draft_eml(draft)
    draft.eml_file = eml_path

    return {
        "success": True,
        "mode": "dry-run",
        "data": {
            "to": draft.to,
            "subject": draft.subject,
            "report_date": draft.report_date,
            "eml_file": eml_path,
            "generated_at": draft.generated_at,
        },
    }


@router.post("/send")
def handle_send_email(body: SendRequest):
    note = None

    if body.markdown_content:
        note = PulseNote(
            report_date=body.report_date or datetime.now().strftime("%Y-%m-%d"),
            period_start="",
            period_end="",
            total_reviews=0,
            average_rating=0,
            generated_at=datetime.now().isoformat(),
            md_file="",
            txt_file="",
            markdown_content=body.markdown_content,
            plaintext_content=body.plaintext_content or body.markdown_content,
        )
    else:
        note = _resolve_note(body.report_date)

    draft = compose_email(
        note=note,
        recipient=body.recipient,
        recipient_name=body.recipient_name,
    )

    if not body.send:
        eml_path = save_draft_eml(draft)
        return {
            "success": True,
            "mode": "dry-run",
            "data": {
                "to": draft.to,
                "subject": draft.subject,
                "report_date": draft.report_date,
                "eml_file": eml_path,
            },
        }

    try:
        send_email(draft)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "success": True,
        "mode": "sent",
        "data": {
            "to": draft.to,
            "subject": draft.subject,
            "report_date": draft.report_date,
        },
    }


@router.get("/download/{report_date}")
def handle_download_eml(report_date: str):
    eml_path = WEEKLY_NOTES_DIR / f"pulse-{report_date}.eml"
    if not eml_path.exists():
        raise HTTPException(status_code=404, detail=f"No .eml file for {report_date}. Save a draft first.")

    return FileResponse(
        path=str(eml_path),
        media_type="message/rfc822",
        filename=f"pulse-{report_date}.eml",
    )


def _resolve_note(report_date: str | None):
    if report_date:
        note = load_note(report_date)
        if not note:
            raise HTTPException(
                status_code=404,
                detail=f"No pulse note found for {report_date}. Run Phase 3 first.",
            )
        return note

    note = load_latest_note()
    if not note:
        raise HTTPException(
            status_code=400,
            detail="No pulse notes found. Run Phase 3 first.",
        )
    return note

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from src.common.constants import WEEKLY_NOTES_DIR, settings
from src.common.models import EmailDraft

logger = logging.getLogger(__name__)


def save_draft_eml(draft: EmailDraft) -> str:
    """
    Dry-run: write the email as an .eml file (RFC 2822) without connecting to SMTP.
    Returns the file path.
    """
    msg = _build_mime_message(draft)

    WEEKLY_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    eml_path = WEEKLY_NOTES_DIR / f"pulse-{draft.report_date}.eml"
    eml_path.write_text(msg.as_string(), encoding="utf-8")

    logger.info("Draft email saved to %s", eml_path.name)
    return str(eml_path)


def send_email(draft: EmailDraft) -> None:
    """
    Send the email via SMTP with TLS.
    Requires EMAIL_SENDER and EMAIL_PASSWORD in .env.
    """
    sender = settings.email_sender
    password = settings.email_password

    if not sender or not password:
        raise RuntimeError(
            "EMAIL_SENDER and EMAIL_PASSWORD must be set in .env to send emails."
        )

    msg = _build_mime_message(draft)

    logger.info("Connecting to %s:%s ...", settings.smtp_host, settings.smtp_port)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, [draft.to], msg.as_string())

    logger.info("Email sent to %s", draft.to)


def _build_mime_message(draft: EmailDraft) -> MIMEMultipart:
    """Build a multipart/alternative MIME message (plain + HTML)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = draft.subject
    msg["From"] = f'"GROWW Review Pulse" <{settings.email_sender or "noreply@groww.in"}>'
    msg["To"] = draft.to

    msg.attach(MIMEText(draft.plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(draft.html_body, "html", "utf-8"))

    return msg

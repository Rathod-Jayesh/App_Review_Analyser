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
    Send the email via SMTP.
    Tries SSL on port 465 first (works on Render/cloud),
    falls back to STARTTLS on port 587 (works locally).
    """
    sender = settings.email_sender
    password = settings.email_password

    if not sender or not password:
        raise RuntimeError(
            "EMAIL_SENDER and EMAIL_PASSWORD must be set in .env to send emails."
        )

    msg = _build_mime_message(draft)

    try:
        logger.info("Trying SMTP SSL on %s:465 ...", settings.smtp_host)
        with smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=30) as server:
            server.login(sender, password)
            server.sendmail(sender, [draft.to], msg.as_string())
        logger.info("Email sent to %s (SSL/465)", draft.to)
        return
    except Exception as ssl_err:
        logger.warning("SSL/465 failed: %s — trying STARTTLS/587", ssl_err)

    try:
        logger.info("Trying SMTP STARTTLS on %s:587 ...", settings.smtp_host)
        with smtplib.SMTP(settings.smtp_host, 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, [draft.to], msg.as_string())
        logger.info("Email sent to %s (STARTTLS/587)", draft.to)
        return
    except Exception as tls_err:
        logger.error("STARTTLS/587 also failed: %s", tls_err)
        raise RuntimeError(
            f"Could not send email. SSL/465: {ssl_err} | STARTTLS/587: {tls_err}"
        )


def _build_mime_message(draft: EmailDraft) -> MIMEMultipart:
    """Build a multipart/alternative MIME message (plain + HTML)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = draft.subject
    msg["From"] = f'"GROWW Review Pulse" <{settings.email_sender or "noreply@groww.in"}>'
    msg["To"] = draft.to

    msg.attach(MIMEText(draft.plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(draft.html_body, "html", "utf-8"))

    return msg

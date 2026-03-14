from __future__ import annotations

import logging
import smtplib
import socket
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from src.common.constants import WEEKLY_NOTES_DIR, settings
from src.common.models import EmailDraft

logger = logging.getLogger(__name__)

_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET] or responses


def save_draft_eml(draft: EmailDraft) -> str:
    msg = _build_mime_message(draft)

    WEEKLY_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    eml_path = WEEKLY_NOTES_DIR / f"pulse-{draft.report_date}.eml"
    eml_path.write_text(msg.as_string(), encoding="utf-8")

    logger.info("Draft email saved to %s", eml_path.name)
    return str(eml_path)


def send_email(draft: EmailDraft) -> None:
    """
    Send email. Uses Resend API (HTTP) if RESEND_API_KEY is set,
    otherwise falls back to Gmail SMTP.
    """
    if settings.resend_api_key:
        _send_via_resend(draft)
    else:
        _send_via_smtp(draft)


def _send_via_resend(draft: EmailDraft) -> None:
    """Send email via Resend HTTP API — works on all cloud platforms."""
    sender = "Groww Review Analyser <onboarding@resend.dev>"
    logger.info("Sending via Resend API from %s to %s ...", sender, draft.to)

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": sender,
            "to": [draft.to],
            "subject": draft.subject,
            "html": draft.html_body,
            "text": draft.plain_body,
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        error_detail = resp.json().get("message", resp.text)
        raise RuntimeError(f"Resend API error: {error_detail}")

    logger.info("Email sent to %s via Resend", draft.to)


def _send_via_smtp(draft: EmailDraft) -> None:
    """Send email via Gmail SMTP — works locally and on GitHub Actions."""
    sender = settings.email_sender
    password = settings.email_password

    if not sender or not password:
        raise RuntimeError(
            "EMAIL_SENDER and EMAIL_PASSWORD must be set in .env to send emails."
        )

    msg = _build_mime_message(draft)
    host = settings.smtp_host

    socket.getaddrinfo = _ipv4_only_getaddrinfo
    smtp_err = ""

    try:
        logger.info("Trying SMTP SSL on %s:465 ...", host)
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, 465, timeout=30, context=ctx) as server:
            server.login(sender, password)
            server.sendmail(sender, [draft.to], msg.as_string())
        logger.info("Email sent to %s (SSL/465)", draft.to)
        return
    except Exception as exc:
        smtp_err = str(exc)
        logger.warning("SSL/465 failed: %s", exc)
    finally:
        socket.getaddrinfo = _original_getaddrinfo

    socket.getaddrinfo = _ipv4_only_getaddrinfo

    try:
        logger.info("Trying SMTP STARTTLS on %s:587 ...", host)
        with smtplib.SMTP(host, 587, timeout=30) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, [draft.to], msg.as_string())
        logger.info("Email sent to %s (STARTTLS/587)", draft.to)
        return
    except Exception as exc:
        logger.error("STARTTLS/587 also failed: %s", exc)
        raise RuntimeError(
            f"SMTP blocked on this platform. Set RESEND_API_KEY for cloud email. "
            f"SSL/465: {smtp_err} | STARTTLS/587: {exc}"
        )
    finally:
        socket.getaddrinfo = _original_getaddrinfo


def _build_mime_message(draft: EmailDraft) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = draft.subject
    msg["From"] = f'"Groww Review Analyser" <{settings.email_sender or "noreply@groww.in"}>'
    msg["To"] = draft.to

    msg.attach(MIMEText(draft.plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(draft.html_body, "html", "utf-8"))

    return msg

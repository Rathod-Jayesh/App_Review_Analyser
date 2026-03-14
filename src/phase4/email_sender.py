from __future__ import annotations

import logging
import smtplib
import socket
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from src.common.constants import WEEKLY_NOTES_DIR, settings
from src.common.models import EmailDraft

logger = logging.getLogger(__name__)

_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(*args, **kwargs):
    """Force IPv4 resolution — fixes 'Network is unreachable' on cloud platforms."""
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
    Send email via Gmail SMTP.
    Forces IPv4 to avoid 'Network is unreachable' on cloud platforms.
    Tries SSL/465 first, then STARTTLS/587.
    """
    sender = settings.email_sender
    password = settings.email_password

    if not sender or not password:
        raise RuntimeError(
            "EMAIL_SENDER and EMAIL_PASSWORD must be set in .env to send emails."
        )

    msg = _build_mime_message(draft)
    host = settings.smtp_host

    socket.getaddrinfo = _ipv4_only_getaddrinfo

    try:
        try:
            logger.info("Trying SMTP SSL on %s:465 ...", host)
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, 465, timeout=30, context=ctx) as server:
                server.login(sender, password)
                server.sendmail(sender, [draft.to], msg.as_string())
            logger.info("Email sent to %s (SSL/465)", draft.to)
            return
        except Exception as ssl_err:
            logger.warning("SSL/465 failed: %s — trying STARTTLS/587", ssl_err)

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
        except Exception as tls_err:
            logger.error("STARTTLS/587 also failed: %s", tls_err)
            raise RuntimeError(
                f"Could not send email. SSL/465: {ssl_err} | STARTTLS/587: {tls_err}"
            )
    finally:
        socket.getaddrinfo = _original_getaddrinfo


def _build_mime_message(draft: EmailDraft) -> MIMEMultipart:
    """Build a multipart/alternative MIME message (plain + HTML)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = draft.subject
    msg["From"] = f'"GROWW Review Pulse" <{settings.email_sender or "noreply@groww.in"}>'
    msg["To"] = draft.to

    msg.attach(MIMEText(draft.plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(draft.html_body, "html", "utf-8"))

    return msg

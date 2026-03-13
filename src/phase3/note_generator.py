from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from src.common.constants import WEEKLY_NOTES_DIR
from src.common.gemini_client import call_gemini
from src.common.models import PulseNote
from src.phase3.data_aggregator import WeeklyAggregation

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a product communications writer at GROWW, an Indian fintech app
for stock trading and mutual fund investments.

Using the themed review data below, write a concise Weekly Review Pulse note.

FORMAT — follow these sections exactly:

# GROWW Weekly Review Pulse — {date}

**Period:** {start} to {end} | **Reviews analysed:** {count} | **Avg rating:** {rating}/5

## Top Themes
For each of the top 3 themes (ranked by review volume), write:
- **Theme Name** ({count} reviews, {pct}%) — a one-sentence summary of user sentiment.

## Real User Quotes
Pick exactly 3 verbatim quotes from the provided reviews:
1. One positive quote (4-5★)
2. One critical quote (1-2★)
3. One insightful/constructive quote (any rating)
Format: > "quote text" — {rating}★

## Action Ideas
List exactly 3 specific, actionable recommendations:
1. **Action Title** (priority: high/medium/low) — 1-sentence description. Related theme: {theme}.

RULES:
- Keep the entire note UNDER 400 words.
- Quotes MUST be verbatim from the provided reviews — NEVER fabricate.
- If a quote contains a personal name, replace it with [User].
- Do NOT include any PII (emails, phone numbers, account IDs).
- Use plain Markdown only. No code blocks, no HTML."""


def _build_user_prompt(agg: WeeklyAggregation) -> str:
    theme_sections: list[str] = []

    for tb in agg.theme_breakdown:
        sample_reviews = tb.reviews[:20]
        review_lines = "\n".join(
            f'- ({r.rating}★) "{r.text}"' for r in sample_reviews
        )
        pct = round(len(tb.reviews) / agg.total_count * 100, 1) if agg.total_count else 0
        theme_sections.append(
            f"### {tb.theme.name} ({len(tb.reviews)} reviews, {pct}%, avg {tb.avg_rating}★)\n"
            f"{review_lines}"
        )

    theme_text = "\n\n".join(theme_sections)

    return f"""Report date: {agg.report_date}
Period: {agg.period_start} to {agg.period_end}
Total reviews: {agg.total_count}
Average rating: {agg.average_rating}/5
Rating distribution: {json.dumps(agg.rating_distribution)}

THEMED REVIEW DATA:
{theme_text}

Write the Weekly Review Pulse note now. Remember: under 400 words, verbatim quotes only."""


def _markdown_to_plaintext(md: str) -> str:
    """Strip Markdown formatting to produce an email-friendly plain-text version."""
    text = md
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^>\s*", "  ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate_pulse_note(agg: WeeklyAggregation) -> PulseNote:
    """Call Gemini to produce the weekly pulse note as Markdown."""
    logger.info(
        "Generating pulse note for %s (%d reviews)",
        agg.report_date,
        agg.total_count,
    )

    user_prompt = _build_user_prompt(agg)

    markdown_content = call_gemini(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.4,
        json_mode=False,
    )

    plaintext_content = _markdown_to_plaintext(markdown_content)

    md_path, txt_path = _save_pulse_files(agg.report_date, markdown_content, plaintext_content)

    note = PulseNote(
        report_date=agg.report_date,
        period_start=agg.period_start,
        period_end=agg.period_end,
        total_reviews=agg.total_count,
        average_rating=agg.average_rating,
        markdown_content=markdown_content,
        plaintext_content=plaintext_content,
        generated_at=datetime.now().isoformat(),
        md_file=str(md_path),
        txt_file=str(txt_path),
    )

    _save_note_json(note)
    return note


def _save_pulse_files(
    report_date: str,
    markdown: str,
    plaintext: str,
) -> tuple[Path, Path]:
    """Save pulse-YYYY-MM-DD.md and pulse-YYYY-MM-DD.txt."""
    WEEKLY_NOTES_DIR.mkdir(parents=True, exist_ok=True)

    md_path = WEEKLY_NOTES_DIR / f"pulse-{report_date}.md"
    txt_path = WEEKLY_NOTES_DIR / f"pulse-{report_date}.txt"

    md_path.write_text(markdown, encoding="utf-8")
    txt_path.write_text(plaintext, encoding="utf-8")

    logger.info("Saved pulse note: %s, %s", md_path.name, txt_path.name)
    return md_path, txt_path


def _save_note_json(note: PulseNote) -> None:
    """Also persist structured metadata as JSON for API retrieval."""
    WEEKLY_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = WEEKLY_NOTES_DIR / f"pulse-{note.report_date}.json"
    filepath.write_text(
        json.dumps(note.model_dump(), indent=2),
        encoding="utf-8",
    )


def load_note(report_date: str) -> PulseNote | None:
    filepath = WEEKLY_NOTES_DIR / f"pulse-{report_date}.json"
    if not filepath.exists():
        return None
    try:
        raw = json.loads(filepath.read_text(encoding="utf-8"))
        return PulseNote(**raw)
    except (json.JSONDecodeError, Exception):
        return None


def load_latest_note() -> PulseNote | None:
    WEEKLY_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(WEEKLY_NOTES_DIR.glob("pulse-*.json"), reverse=True)
    if not files:
        return None
    try:
        raw = json.loads(files[0].read_text(encoding="utf-8"))
        return PulseNote(**raw)
    except (json.JSONDecodeError, Exception):
        return None


def list_note_dates() -> list[str]:
    WEEKLY_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        [
            f.stem.replace("pulse-", "")
            for f in WEEKLY_NOTES_DIR.glob("pulse-*.json")
        ],
        reverse=True,
    )

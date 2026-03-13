#!/usr/bin/env python3
"""GROWW App Review Analyser CLI - run the full pipeline from the terminal."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from src.common.storage import load_reviews, save_reviews
from src.phase1.play_store_scraper import fetch_play_store_reviews
from src.phase1.review_normalizer import normalize_reviews
from src.phase2.review_classifier import classify_all_reviews, load_classifications
from src.phase2.theme_generator import generate_themes, load_themes
from src.phase3.data_aggregator import aggregate_data
from src.phase3.note_generator import generate_pulse_note, load_latest_note
from src.phase4.email_composer import compose_email
from src.phase4.email_sender import save_draft_eml, send_email


def cmd_fetch(weeks: int = 12, max_reviews: int = 3000) -> int:
    print(f"[Phase 1] Fetching reviews (last {weeks} weeks, max {max_reviews})...")
    try:
        raw = fetch_play_store_reviews(weeks=weeks, max_reviews=max_reviews)
        print(f"  Fetched {len(raw)} raw reviews")
        reviews = normalize_reviews(play_store_raw=raw, app_store_raw=[])
        print(f"  Normalized to {len(reviews)} reviews")
        save_reviews(reviews)
        print(f"  Saved to data/reviews.json")
        return 0
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 1


def cmd_themes() -> int:
    print("[Phase 2a] Generating themes...")
    try:
        store = load_reviews()
        if not store or not store.reviews:
            print("  Error: No reviews found. Run 'fetch' first.", file=sys.stderr)
            return 1
        theme_store = generate_themes(store.reviews)
        print(f"  Generated {len(theme_store.themes)} themes")
        return 0
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 1


def cmd_classify() -> int:
    print("[Phase 2b] Classifying reviews (may take ~12 min)...")
    try:
        theme_store = load_themes()
        if not theme_store:
            print("  Error: No themes found. Run 'themes' first.", file=sys.stderr)
            return 1
        review_store = load_reviews()
        if not review_store or not review_store.reviews:
            print("  Error: No reviews found. Run 'fetch' first.", file=sys.stderr)
            return 1
        classification_store = classify_all_reviews(
            theme_store.themes, review_store.reviews
        )
        print(f"  Classified {classification_store.total_classified} reviews")
        return 0
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 1


def cmd_generate() -> int:
    print("[Phase 3] Generating weekly note...")
    try:
        review_store = load_reviews()
        if not review_store or not review_store.reviews:
            print("  Error: No reviews found. Run 'fetch' first.", file=sys.stderr)
            return 1
        theme_store = load_themes()
        if not theme_store:
            print("  Error: No themes found. Run 'themes' first.", file=sys.stderr)
            return 1
        classification_store = load_classifications()
        if not classification_store:
            print("  Error: No classifications found. Run 'classify' first.", file=sys.stderr)
            return 1

        report_date = datetime.now().strftime("%Y-%m-%d")
        aggregation = aggregate_data(
            review_store.reviews,
            theme_store.themes,
            classification_store.classifications,
            report_date,
        )
        note = generate_pulse_note(aggregation)
        print(f"  Generated pulse note for {note.report_date}")
        return 0
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 1


def cmd_email(recipient: str, name: str | None, do_send: bool) -> int:
    print("[Phase 4] Composing email...")
    try:
        note = load_latest_note()
        if not note:
            print("  Error: No pulse note found. Run 'generate' first.", file=sys.stderr)
            return 1
        draft = compose_email(note, recipient, name)
        save_draft_eml(draft)
        print(f"  Draft saved to data/weekly-notes/pulse-{draft.report_date}.eml")
        if do_send:
            send_email(draft)
            print(f"  Email sent to {recipient}")
        else:
            print("  Use --send to actually send the email")
        return 0
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 1


def cmd_run_all(recipient: str, name: str | None, do_send: bool, weeks: int = 12, max_reviews: int = 3000) -> int:
    steps = [
        ("fetch", lambda: cmd_fetch(weeks=weeks, max_reviews=max_reviews)),
        ("themes", cmd_themes),
        ("classify", cmd_classify),
        ("generate", cmd_generate),
    ]
    for label, fn in steps:
        code = fn()
        if code != 0:
            print(f"Pipeline stopped at '{label}'", file=sys.stderr)
            return code
    return cmd_email(recipient, name, do_send)


def cmd_status() -> int:
    review_store = load_reviews()
    theme_store = load_themes()
    classification_store = load_classifications()
    note = load_latest_note()

    review_count = len(review_store.reviews) if review_store else 0
    theme_count = len(theme_store.themes) if theme_store else 0
    classification_count = (
        classification_store.total_classified if classification_store else 0
    )
    latest_note = note.report_date if note else None

    print("Data status:")
    print(f"  Reviews: {review_count}")
    print(f"  Themes: {theme_count}")
    print(f"  Classifications: {classification_count}")
    print(f"  Latest note: {latest_note or 'none'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="GROWW App Review Analyser - run the pipeline from the terminal",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Run Phase 1: fetch and normalize reviews")
    fetch_parser.add_argument("--weeks", type=int, default=12, help="Fetch reviews from last N weeks (default: 12)")
    fetch_parser.add_argument("--max-reviews", type=int, default=3000, help="Max reviews to fetch (default: 3000)")
    subparsers.add_parser("themes", help="Run Phase 2a: generate themes")
    subparsers.add_parser(
        "classify",
        help="Run Phase 2b: classify reviews (long running, ~12 min)",
    )
    subparsers.add_parser("generate", help="Run Phase 3: generate weekly note")

    email_parser = subparsers.add_parser("email", help="Run Phase 4: compose and optionally send email")
    email_parser.add_argument("--recipient", required=True, help="Recipient email address")
    email_parser.add_argument("--name", default=None, help="Recipient name for greeting")
    email_parser.add_argument("--send", action="store_true", help="Actually send the email via SMTP")

    run_all_parser = subparsers.add_parser(
        "run-all",
        help="Run all phases sequentially",
    )
    run_all_parser.add_argument("--recipient", required=True, help="Recipient email address")
    run_all_parser.add_argument("--name", default=None, help="Recipient name for greeting")
    run_all_parser.add_argument("--weeks", type=int, default=12, help="Fetch reviews from last N weeks (default: 12)")
    run_all_parser.add_argument("--max-reviews", type=int, default=3000, help="Max reviews to fetch (default: 3000)")
    run_all_parser.add_argument("--send", action="store_true", help="Actually send the email via SMTP")

    subparsers.add_parser("status", help="Show current data status")

    args = parser.parse_args()

    handlers = {
        "fetch": lambda: cmd_fetch(weeks=args.weeks, max_reviews=args.max_reviews),
        "themes": lambda: cmd_themes(),
        "classify": lambda: cmd_classify(),
        "generate": lambda: cmd_generate(),
        "email": lambda: cmd_email(args.recipient, args.name, args.send),
        "run-all": lambda: cmd_run_all(args.recipient, args.name, args.send, weeks=args.weeks, max_reviews=args.max_reviews),
        "status": lambda: cmd_status(),
    }
    return handlers[args.command]()


if __name__ == "__main__":
    sys.exit(main())

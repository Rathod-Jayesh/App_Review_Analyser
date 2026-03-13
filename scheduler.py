#!/usr/bin/env python3
"""
Weekly Pulse Scheduler
Runs the full pipeline (fetch → themes → classify → generate → send email)
every Monday at 3:35 PM IST automatically.

Usage:
    python scheduler.py              # start the scheduler (runs in foreground)
    python scheduler.py --run-now    # run immediately once, then start scheduler
    python scheduler.py --day friday # change the day (default: monday)

Recipient: travelerjayesh@gmail.com (fixed)
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

import schedule

IST = timezone(timedelta(hours=5, minutes=30))

RECIPIENT_EMAIL = "travelerjayesh@gmail.com"
RECIPIENT_NAME = "Jayesh"

FETCH_WEEKS = 8
MAX_REVIEWS = 1000

SCHEDULE_TIME = "12:35"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_weekly_pulse() -> None:
    """Execute the full pipeline via the CLI and send the email."""
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    logger.info("Starting weekly pulse pipeline at %s", now_ist)

    cmd = [
        sys.executable, "cli.py", "run-all",
        "--recipient", RECIPIENT_EMAIL,
        "--name", RECIPIENT_NAME,
        "--weeks", str(FETCH_WEEKS),
        "--max-reviews", str(MAX_REVIEWS),
        "--send",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,
        )

        for line in result.stdout.strip().splitlines():
            logger.info("  %s", line)

        if result.returncode != 0:
            logger.error("Pipeline failed (exit code %d)", result.returncode)
            for line in result.stderr.strip().splitlines():
                logger.error("  %s", line)
        else:
            logger.info("Pipeline completed successfully. Email sent to %s", RECIPIENT_EMAIL)

    except subprocess.TimeoutExpired:
        logger.error("Pipeline timed out after 30 minutes")
    except Exception as exc:
        logger.error("Pipeline error: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Weekly Pulse Scheduler — runs full pipeline on a schedule",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the pipeline immediately once, then continue with the schedule",
    )
    parser.add_argument(
        "--day",
        default="monday",
        choices=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        help="Day of the week to run (default: monday)",
    )
    parser.add_argument(
        "--time",
        default=SCHEDULE_TIME,
        help="Time to run in HH:MM format, IST (default: 15:35)",
    )
    args = parser.parse_args()

    day_fn = getattr(schedule.every(), args.day)
    day_fn.at(args.time).do(run_weekly_pulse)

    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    logger.info("Scheduler started at %s", now_ist)
    logger.info("Scheduled: every %s at %s IST", args.day.capitalize(), args.time)
    logger.info("Recipient: %s (%s)", RECIPIENT_EMAIL, RECIPIENT_NAME)
    logger.info("Next run: %s", schedule.next_run())

    if args.run_now:
        logger.info("--run-now flag set, executing immediately...")
        run_weekly_pulse()

    logger.info("Waiting for scheduled runs. Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    main()

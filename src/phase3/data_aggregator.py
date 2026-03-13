from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.common.models import ClassifiedReview, Review, Theme


@dataclass
class ThemeBreakdown:
    theme: Theme
    reviews: list[Review] = field(default_factory=list)
    avg_rating: float = 0.0


@dataclass
class WeeklyAggregation:
    report_date: str
    period_start: str
    period_end: str
    reviews: list[Review] = field(default_factory=list)
    total_count: int = 0
    average_rating: float = 0.0
    rating_distribution: dict[int, int] = field(default_factory=dict)
    theme_breakdown: list[ThemeBreakdown] = field(default_factory=list)


def aggregate_data(
    reviews: list[Review],
    themes: list[Theme],
    classifications: list[ClassifiedReview],
    report_date: str | None = None,
    weeks: int = 12,
) -> WeeklyAggregation:
    """
    Aggregate reviews, themes, and classifications into a structured
    object that the note generator can consume.

    report_date: ISO date string (YYYY-MM-DD). Defaults to today.
    weeks: configured week range — used for period_start so the report
           reflects the intended timeframe, not just the fetched data span.
    """
    if not reviews:
        raise ValueError("No reviews to aggregate")

    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d")

    report_dt = datetime.strptime(report_date, "%Y-%m-%d")
    period_start = (report_dt - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    period_end = report_date

    rating_dist: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        rating_dist[r.rating] = rating_dist.get(r.rating, 0) + 1

    total = len(reviews)
    avg_rating = sum(r.rating for r in reviews) / total if total else 0.0

    class_map: dict[str, str] = {c.review_id: c.theme_id for c in classifications}
    review_map: dict[str, Review] = {r.id: r for r in reviews}

    theme_breakdowns: list[ThemeBreakdown] = []
    for theme in themes:
        theme_reviews = [
            review_map[rid]
            for rid, tid in class_map.items()
            if tid == theme.id and rid in review_map
        ]
        t_avg = (
            sum(r.rating for r in theme_reviews) / len(theme_reviews)
            if theme_reviews
            else 0.0
        )
        theme_breakdowns.append(
            ThemeBreakdown(
                theme=theme,
                reviews=theme_reviews,
                avg_rating=round(t_avg, 2),
            )
        )

    theme_breakdowns.sort(key=lambda tb: len(tb.reviews), reverse=True)

    return WeeklyAggregation(
        report_date=report_date,
        period_start=period_start,
        period_end=period_end,
        reviews=reviews,
        total_count=total,
        average_rating=round(avg_rating, 2),
        rating_distribution=rating_dist,
        theme_breakdown=theme_breakdowns,
    )

from datetime import datetime, timedelta


def get_week_label(dt: datetime) -> str:
    """Return ISO week label like '2026-W11'."""
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def get_cutoff_date(weeks: int) -> datetime:
    """Return the datetime N weeks ago (midnight)."""
    cutoff = datetime.now() - timedelta(weeks=weeks)
    return cutoff.replace(hour=0, minute=0, second=0, microsecond=0)


def get_week_start(week_label: str) -> datetime:
    """Return the Monday of the given ISO week."""
    return datetime.strptime(week_label + "-1", "%G-W%V-%u")


def get_week_end(week_label: str) -> datetime:
    """Return the Sunday of the given ISO week."""
    return datetime.strptime(week_label + "-7", "%G-W%V-%u")

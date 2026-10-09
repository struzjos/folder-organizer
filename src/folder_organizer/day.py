"""Logical day: a new day starts at the configured reset time, not at midnight."""

from datetime import date, datetime, time, timedelta


def parse_time(value: object) -> time:
    """Parse "HH:MM" into a time. Raises ValueError for anything else."""
    if not isinstance(value, str):
        raise ValueError(f"expected 'HH:MM', got {value!r}")
    hours, sep, minutes = value.strip().partition(":")
    if not sep:
        raise ValueError(f"expected 'HH:MM', got {value!r}")
    return time(int(hours), int(minutes))


def logical_date(now: datetime, reset: time) -> date:
    """The day `now` belongs to. With reset 04:00, 02:30 on Oct 10 still counts as Oct 9."""
    return (now - timedelta(hours=reset.hour, minutes=reset.minute)).date()


def format_day(day: date) -> str:
    """Short display form, e.g. "Fri 2026-10-09"."""
    return f"{day:%a} {day.isoformat()}"

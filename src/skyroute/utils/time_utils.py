"""Time-related utility helpers."""

from __future__ import annotations


def hours_to_minutes(hours: float) -> float:
    """Convert hours to minutes."""
    return hours * 60.0


def minutes_to_hours(minutes: float) -> float:
    """Convert minutes to hours."""
    return minutes / 60.0


def format_minutes(minutes: float) -> str:
    """Format a duration in minutes as a friendly string."""
    total_minutes = int(round(minutes))
    hours, remaining_minutes = divmod(total_minutes, 60)
    return f"{hours}h {remaining_minutes}m"

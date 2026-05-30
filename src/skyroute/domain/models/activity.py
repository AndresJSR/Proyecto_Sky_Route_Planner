"""Activity domain model."""

from __future__ import annotations

from dataclasses import dataclass

from ..enums import ActivityType


@dataclass(slots=True)
class Activity:
    """Represents an activity available at a destination."""

    id: str
    name: str
    activity_type: ActivityType
    location_code: str | None = None
    duration_hours: float | None = None
    cost_usd: float | None = None

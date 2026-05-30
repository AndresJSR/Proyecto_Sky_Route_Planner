"""Activity record domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .activity import Activity


@dataclass(slots=True)
class ActivityRecord:
    """Stores the completion state of an activity."""

    activity_id: str
    activity: Activity | None = None
    completed_at: datetime | None = None
    notes: str | None = None

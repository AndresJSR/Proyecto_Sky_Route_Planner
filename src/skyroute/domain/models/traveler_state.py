"""Traveler state domain model."""

from __future__ import annotations

from dataclasses import dataclass, field

from .activity_record import ActivityRecord
from .job_record import JobRecord
from .visited_destination import VisitedDestination


@dataclass(slots=True)
class TravelerState:
    """Tracks the current state of a traveler during planning."""

    current_airport_code: str
    budget_usd: float = 0.0
    elapsed_hours: float = 0.0
    visited_destinations: list[VisitedDestination] = field(default_factory=list)
    activity_records: list[ActivityRecord] = field(default_factory=list)
    job_records: list[JobRecord] = field(default_factory=list)

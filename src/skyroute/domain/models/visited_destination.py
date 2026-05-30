"""Visited destination domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class VisitedDestination:
    """Represents a destination already visited by the traveler."""

    airport_code: str
    visited_at: datetime | None = None
    notes: str | None = None

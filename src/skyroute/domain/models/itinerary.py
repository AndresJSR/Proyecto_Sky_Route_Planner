"""Itinerary domain model."""

from __future__ import annotations

from dataclasses import dataclass, field

from .activity_record import ActivityRecord
from .flight_segment import FlightSegment


@dataclass(slots=True)
class Itinerary:
    """Represents a planned trip with flights and activities."""

    traveler_name: str
    flight_segments: list[FlightSegment] = field(default_factory=list)
    activity_records: list[ActivityRecord] = field(default_factory=list)
    total_distance_km: float = 0.0
    total_duration_minutes: float = 0.0
    total_cost_usd: float = 0.0

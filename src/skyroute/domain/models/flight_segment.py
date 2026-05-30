"""Flight segment domain model."""

from __future__ import annotations

from dataclasses import dataclass

from .route import Route


@dataclass(slots=True)
class FlightSegment:
    """Represents a single leg inside an itinerary."""

    origin_code: str
    destination_code: str
    distance_km: float
    duration_minutes: float
    cost_usd: float
    route: Route | None = None

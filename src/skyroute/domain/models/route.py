"""Route domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Route:
    """Represents a directed edge between two airports."""

    origin_code: str
    destination_code: str
    distance_km: float
    duration_minutes: float
    cost_usd: float
    is_blocked: bool = False

"""Aircraft domain model."""

from __future__ import annotations

from dataclasses import dataclass

from ..enums import AircraftType


@dataclass(slots=True)
class Aircraft:
    """Represents an aircraft configuration used by the planner."""

    id: str
    aircraft_type: AircraftType
    cost_per_km: float
    time_per_km: float
    capacity: int | None = None

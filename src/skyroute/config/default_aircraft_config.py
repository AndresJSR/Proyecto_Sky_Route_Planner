"""Default aircraft configuration values."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import AircraftType


@dataclass(frozen=True, slots=True)
class AircraftPerformanceProfile:
    """Stores cost and time coefficients for an aircraft type."""

    cost_per_km_usd: float
    time_per_km_minutes: float


DEFAULT_AIRCRAFT_PROFILES: dict[AircraftType, AircraftPerformanceProfile] = {
    AircraftType.COMMERCIAL: AircraftPerformanceProfile(cost_per_km_usd=0.18, time_per_km_minutes=0.7),
    AircraftType.REGIONAL: AircraftPerformanceProfile(cost_per_km_usd=0.25, time_per_km_minutes=1.1),
    AircraftType.PROPELLER: AircraftPerformanceProfile(cost_per_km_usd=0.12, time_per_km_minutes=2.5),
}

MINIMUM_BUDGET_PERCENT_FOR_JOBS: float = 0.35
LODGING_INTERVAL_HOURS: int = 20
FOOD_INTERVAL_HOURS: int = 8

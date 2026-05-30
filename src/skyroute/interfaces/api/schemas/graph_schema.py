"""Graph API schemas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AirportSchema:
    """Airport payload for API requests and responses."""

    code: str
    name: str
    city: str
    country: str
    latitude: float | None = None
    longitude: float | None = None


@dataclass(slots=True)
class RouteSchema:
    """Route payload for API requests and responses."""

    origin_code: str
    destination_code: str
    distance_km: float
    duration_minutes: float
    cost_usd: float


@dataclass(slots=True)
class GraphSchema:
    """Graph payload for API responses."""

    airports: list[AirportSchema] = field(default_factory=list)
    routes: list[RouteSchema] = field(default_factory=list)

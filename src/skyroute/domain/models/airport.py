"""Airport domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Airport:
    """Represents an airport node in the air route graph."""

    code: str
    name: str
    city: str
    country: str
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool = True

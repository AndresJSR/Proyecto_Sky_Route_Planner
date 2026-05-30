"""Aircraft type definitions."""

from __future__ import annotations

from enum import Enum


class AircraftType(str, Enum):
    """Supported aircraft categories."""

    COMMERCIAL = "COMMERCIAL"
    REGIONAL = "REGIONAL"
    PROPELLER = "PROPELLER"

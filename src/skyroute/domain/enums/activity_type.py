"""Activity type definitions."""

from __future__ import annotations

from enum import Enum


class ActivityType(str, Enum):
    """Supported activity categories."""

    MANDATORY = "MANDATORY"
    OPTIONAL = "OPTIONAL"
    LODGING = "LODGING"
    FOOD = "FOOD"
    TOUR = "TOUR"
    CULTURAL = "CULTURAL"

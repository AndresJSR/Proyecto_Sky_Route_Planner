"""Trip API schemas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TripRequestSchema:
    """Request payload for trip interruption operations."""

    origin_code: str
    destination_code: str


@dataclass(slots=True)
class TripResponseSchema:
    """Response payload for trip interruption operations."""

    success: bool
    message: str | None = None

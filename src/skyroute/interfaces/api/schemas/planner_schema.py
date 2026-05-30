"""Planner API schemas."""

from __future__ import annotations

from dataclasses import dataclass

from ....domain.enums import OptimizationCriterion


@dataclass(slots=True)
class PlannerRequestSchema:
    """Request payload for a trip planning operation."""

    origin_code: str
    destination_code: str
    criterion: OptimizationCriterion | None = None


@dataclass(slots=True)
class PlannerResponseSchema:
    """Response payload for a trip planning operation."""

    route_codes: list[str]
    total_distance_km: float | None = None
    total_duration_minutes: float | None = None
    total_cost_usd: float | None = None

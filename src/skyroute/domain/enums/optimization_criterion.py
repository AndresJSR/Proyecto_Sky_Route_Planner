"""Route optimization criteria."""

from __future__ import annotations

from enum import Enum


class OptimizationCriterion(str, Enum):
    """Criteria used to optimize routes."""

    DISTANCE = "DISTANCE"
    TIME = "TIME"
    COST = "COST"

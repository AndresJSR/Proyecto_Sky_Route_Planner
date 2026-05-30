"""Planner controller placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ....application.services import BasicPlannerService, AdvancedPlannerService
from ....domain.enums import OptimizationCriterion


@dataclass(slots=True)
class PlannerController:
    """Placeholder controller for planning endpoints."""

    basic_planner_service: BasicPlannerService
    advanced_planner_service: AdvancedPlannerService

    def plan_basic_trip(self, origin_code: str, destination_code: str) -> list[str]:
        """Plan a basic trip."""
        return self.basic_planner_service.plan_trip(origin_code, destination_code)

    def plan_advanced_trip(self, origin_code: str, destination_code: str, criterion: OptimizationCriterion) -> list[str]:
        """Plan an advanced trip."""
        return self.advanced_planner_service.optimize_trip(origin_code, destination_code, criterion)

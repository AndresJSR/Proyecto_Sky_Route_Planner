"""Route optimization placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import OptimizationCriterion
from ..graph import AirRouteGraph


@dataclass(slots=True)
class RouteOptimizer:
    """Skeleton for route optimization strategies."""

    graph: AirRouteGraph

    def optimize(self, origin_code: str, destination_code: str, criterion: OptimizationCriterion) -> list[str]:
        """Optimize a route according to the selected criterion.

        TODO: Support distance, time, and cost optimization modes.
        """
        raise NotImplementedError("RouteOptimizer.optimize is not implemented yet.")

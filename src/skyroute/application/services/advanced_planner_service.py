"""Advanced trip planning service."""

from __future__ import annotations

from dataclasses import dataclass

from ...algorithms import ConstrainedSearch, RouteOptimizer
from ...domain.enums import OptimizationCriterion
from ...graph import AirRouteGraph
from .graph_service import GraphService


@dataclass(slots=True)
class AdvancedPlannerService:
    """Provides extended planning capabilities for future features."""

    graph_service: GraphService
    constrained_search: ConstrainedSearch
    route_optimizer: RouteOptimizer

    @classmethod
    def from_graph(cls, graph: AirRouteGraph) -> "AdvancedPlannerService":
        """Build the service with the default advanced algorithms."""
        graph_service = GraphService(graph)
        return cls(
            graph_service=graph_service,
            constrained_search=ConstrainedSearch(graph),
            route_optimizer=RouteOptimizer(graph),
        )

    def optimize_trip(self, origin_code: str, destination_code: str, criterion: OptimizationCriterion) -> list[str]:
        """Optimize a trip using the selected criterion."""
        return self.route_optimizer.optimize(origin_code, destination_code, criterion)

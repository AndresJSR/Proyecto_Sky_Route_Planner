"""Reporting service placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ...graph import AirRouteGraph
from .graph_service import GraphService


@dataclass(slots=True)
class ReportService:
    """Produces reports for airports, routes, and trip results."""

    graph_service: GraphService

    @classmethod
    def from_graph(cls, graph: AirRouteGraph) -> "ReportService":
        """Build the service from a graph instance."""
        return cls(graph_service=GraphService(graph))

    def generate_network_summary(self) -> dict[str, int]:
        """Return a minimal network summary.

        TODO: Expand the report structure with planning metrics.
        """
        graph = self.graph_service.graph
        return {
            "airports": len(graph.get_all_airports()),
            "routes": len(graph.get_all_routes()),
        }

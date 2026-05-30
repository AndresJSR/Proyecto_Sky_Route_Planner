"""Interruption handling service."""

from __future__ import annotations

from dataclasses import dataclass

from ...graph import AirRouteGraph
from .graph_service import GraphService


@dataclass(slots=True)
class InterruptionService:
    """Handles route blocking and unblocking workflows."""

    graph_service: GraphService

    @classmethod
    def from_graph(cls, graph: AirRouteGraph) -> "InterruptionService":
        """Build the service from a graph instance."""
        return cls(graph_service=GraphService(graph))

    def block_route(self, origin_code: str, destination_code: str) -> None:
        """Block a route from use."""
        self.graph_service.graph.block_route(origin_code, destination_code)

    def unblock_route(self, origin_code: str, destination_code: str) -> None:
        """Restore a blocked route."""
        self.graph_service.graph.unblock_route(origin_code, destination_code)

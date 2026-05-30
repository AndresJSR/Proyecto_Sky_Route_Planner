"""Basic trip planning service."""

from __future__ import annotations

from dataclasses import dataclass

from ...algorithms import DijkstraAlgorithm
from ...graph import AirRouteGraph
from .graph_service import GraphService


@dataclass(slots=True)
class BasicPlannerService:
    """Provides the initial trip planning workflow."""

    graph_service: GraphService
    dijkstra_algorithm: DijkstraAlgorithm

    @classmethod
    def from_graph(cls, graph: AirRouteGraph) -> "BasicPlannerService":
        """Build the service with the default shortest-path algorithm."""
        graph_service = GraphService(graph)
        return cls(graph_service=graph_service, dijkstra_algorithm=DijkstraAlgorithm(graph))

    def plan_trip(self, origin_code: str, destination_code: str) -> list[str]:
        """Plan a basic trip between two airports.

        TODO: Convert the path into a full itinerary structure.
        """
        return self.dijkstra_algorithm.find_shortest_path(origin_code, destination_code)

"""Graph-related application services."""

from __future__ import annotations

from dataclasses import dataclass

from ...domain.models import Airport, Route
from ...graph import AirRouteGraph


@dataclass(slots=True)
class GraphService:
    """Coordinates graph operations without exposing infrastructure details."""

    graph: AirRouteGraph

    def add_airport(self, airport: Airport) -> None:
        """Register an airport in the graph."""
        self.graph.add_airport(airport)

    def add_route(self, route: Route) -> None:
        """Register a route in the graph."""
        self.graph.add_route(route)

    def get_airport(self, airport_code: str) -> Airport | None:
        """Return an airport by code."""
        return self.graph.get_airport(airport_code)

    def get_neighbors(self, airport_code: str) -> list[Route]:
        """Return the outgoing routes for an airport."""
        return self.graph.get_neighbors(airport_code)

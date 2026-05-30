"""Custom adjacency list implementation for air routes."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import Route


@dataclass(slots=True)
class AdjacencyList:
    """Stores outgoing routes for each airport code."""

    data: dict[str, list[Route]] = field(default_factory=dict)

    def add_vertex(self, airport_code: str) -> None:
        """Ensure that an airport code exists in the adjacency list."""
        self.data.setdefault(airport_code, [])

    def add_edge(self, route: Route) -> None:
        """Add a directed route to the adjacency list."""
        self.add_vertex(route.origin_code)
        self.add_vertex(route.destination_code)
        self.data[route.origin_code].append(route)

    def get_neighbors(self, airport_code: str) -> list[Route]:
        """Return all outgoing routes from the given airport."""
        return list(self.data.get(airport_code, []))

    def get_all_routes(self) -> list[Route]:
        """Return every route stored in the graph."""
        routes: list[Route] = []
        for route_list in self.data.values():
            routes.extend(route_list)
        return routes

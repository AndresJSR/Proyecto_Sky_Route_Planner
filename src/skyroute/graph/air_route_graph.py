"""Central graph structure for SkyRoute Planner."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.exceptions import GraphException, RouteNotFoundException
from ..domain.models import Airport, Route
from .adjacency_list import AdjacencyList


@dataclass(slots=True)
class AirRouteGraph:
    """Directed weighted graph of airports and air routes."""

    airports: dict[str, Airport] = field(default_factory=dict)
    adjacency_list: dict[str, list[Route]] = field(default_factory=dict)
    _adjacency: AdjacencyList = field(default_factory=AdjacencyList, init=False, repr=False)

    def __post_init__(self) -> None:
        """Synchronize the public adjacency dictionary with the helper structure."""
        self.adjacency_list = self._adjacency.data

    def add_airport(self, airport: Airport) -> None:
        """Add or register an airport in the graph."""
        self.airports[airport.code] = airport
        self._adjacency.add_vertex(airport.code)

    def add_route(self, route: Route) -> None:
        """Add a directed route between two airports."""
        if route.origin_code not in self.airports or route.destination_code not in self.airports:
            raise GraphException("Both airports must exist before adding a route.")
        self._adjacency.add_edge(route)

    def get_airport(self, airport_code: str) -> Airport | None:
        """Return an airport by code if it exists."""
        return self.airports.get(airport_code)

    def get_neighbors(self, airport_code: str) -> list[Route]:
        """Return the outgoing routes for a given airport."""
        return [route for route in self._adjacency.get_neighbors(airport_code) if not route.is_blocked]

    def block_route(self, origin_code: str, destination_code: str) -> None:
        """Mark a route as blocked."""
        route = self._find_route(origin_code, destination_code)
        route.is_blocked = True

    def unblock_route(self, origin_code: str, destination_code: str) -> None:
        """Mark a route as available again."""
        route = self._find_route(origin_code, destination_code)
        route.is_blocked = False

    def route_exists(self, origin_code: str, destination_code: str) -> bool:
        """Check whether a route exists in the graph."""
        return any(
            route.destination_code == destination_code
            for route in self._adjacency.get_neighbors(origin_code)
        )

    def get_all_airports(self) -> list[Airport]:
        """Return all registered airports."""
        return list(self.airports.values())

    def get_all_routes(self) -> list[Route]:
        """Return all registered routes."""
        return self._adjacency.get_all_routes()

    def _find_route(self, origin_code: str, destination_code: str) -> Route:
        """Locate a route or raise a graph exception."""
        for route in self._adjacency.get_neighbors(origin_code):
            if route.destination_code == destination_code:
                return route
        raise RouteNotFoundException(
            f"Route from {origin_code} to {destination_code} was not found."
        )

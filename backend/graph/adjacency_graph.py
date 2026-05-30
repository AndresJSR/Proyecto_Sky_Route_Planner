from __future__ import annotations

from domain.models.airport import Airport
from domain.models.route import Route


class AdjacencyGraph:
    """
    Directed weighted graph representing the airline route network.

    Implemented from scratch using a dictionary-based adjacency list.
    No external graph libraries are used.

    Internal structure
    ------------------
    _nodes : dict[str, Airport]
        Maps each IATA code to its Airport object (graph nodes).
    _adj   : dict[str, list[Route]]
        Maps each IATA code to the list of outgoing Route objects (graph edges).

    Design decisions
    ----------------
    * Directed graph: adding edge A→B does NOT implicitly add B→A.
      Both directions must be declared explicitly in the JSON, mirroring
      real airline schedules where a route from A to B does not guarantee
      a return flight.
    * Weighted edges: each Route carries distancia_km, and the Aircraft
      model derives cost (USD) and time (min) from it at query time.
    * Blocked routes: the Route.bloqueada flag excludes an edge from
      get_neighbors() without removing it from the structure, making the
      interruption reversible and preserving visual state for the UI.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Airport] = {}
        self._adj: dict[str, list[Route]] = {}

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(self, airport: Airport) -> None:
        """
        Add an airport to the graph.

        Args:
            airport: Airport object to insert.

        Raises:
            ValueError: If a node with the same IATA code already exists.
        """
        if airport.id in self._nodes:
            raise ValueError(f"Node '{airport.id}' already exists in the graph.")
        self._nodes[airport.id] = airport
        self._adj[airport.id] = []

    def get_node(self, airport_id: str) -> Airport:
        """
        Return the Airport for the given IATA code.

        Raises:
            KeyError: If the airport is not in the graph.
        """
        if airport_id not in self._nodes:
            raise KeyError(f"Airport '{airport_id}' not found in the graph.")
        return self._nodes[airport_id]

    def has_node(self, airport_id: str) -> bool:
        """Return True when the airport exists in the graph."""
        return airport_id in self._nodes

    def get_all_nodes(self) -> list[Airport]:
        """Return all airports currently in the graph."""
        return list(self._nodes.values())

    def get_hubs(self) -> list[Airport]:
        """Return only the hub airports."""
        return [a for a in self._nodes.values() if a.es_hub]

    def get_secondary_airports(self) -> list[Airport]:
        """Return only the non-hub (secondary) airports."""
        return [a for a in self._nodes.values() if not a.es_hub]

    def node_count(self) -> int:
        """Return the total number of airports in the graph."""
        return len(self._nodes)

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def add_edge(self, route: Route) -> None:
        """
        Add a directed edge from route.origen to route.destino.

        Both endpoint airports must already exist in the graph before
        calling this method.

        Args:
            route: Route object representing the directed edge.

        Raises:
            KeyError:   If either endpoint airport is not in the graph.
            ValueError: If an edge with the same origin-destination pair
                        already exists.
        """
        if route.origen not in self._nodes:
            raise KeyError(
                f"Origin airport '{route.origen}' not found. "
                "Add the airport node before adding its edges."
            )
        if route.destino not in self._nodes:
            raise KeyError(
                f"Destination airport '{route.destino}' not found. "
                "Add the airport node before adding its edges."
            )
        for existing in self._adj[route.origen]:
            if existing.destino == route.destino:
                raise ValueError(
                    f"Route '{route.origen}' → '{route.destino}' already exists."
                )
        self._adj[route.origen].append(route)

    def get_route(self, origen: str, destino: str) -> Route | None:
        """
        Return the Route from origen to destino, or None if not found.

        Only the direct edge is returned; this method does not traverse
        the graph.
        """
        for route in self._adj.get(origen, []):
            if route.destino == destino:
                return route
        return None

    def has_edge(self, origen: str, destino: str) -> bool:
        """Return True when a direct route from origen to destino exists."""
        return self.get_route(origen, destino) is not None

    def get_neighbors(
        self,
        airport_id: str,
        include_blocked: bool = False,
    ) -> list[Route]:
        """
        Return all outgoing routes from the given airport.

        This is the primary method used by path-finding algorithms to
        traverse the graph. By default, blocked routes are excluded so
        that algorithms automatically respect interruptions without
        needing to check the flag themselves.

        Args:
            airport_id:      IATA code of the origin airport.
            include_blocked: When True, blocked routes are included in
                             the result (e.g. for UI rendering).

        Returns:
            List of Route objects departing from airport_id.

        Raises:
            KeyError: If the airport does not exist in the graph.
        """
        if airport_id not in self._adj:
            raise KeyError(f"Airport '{airport_id}' not found in the graph.")
        routes = self._adj[airport_id]
        if include_blocked:
            return list(routes)
        return [r for r in routes if not r.bloqueada]

    def get_all_edges(self, include_blocked: bool = True) -> list[Route]:
        """Return every edge in the graph."""
        edges: list[Route] = []
        for routes in self._adj.values():
            edges.extend(routes)
        if not include_blocked:
            return [r for r in edges if not r.bloqueada]
        return edges

    def edge_count(self) -> int:
        """Return the total number of edges (including blocked ones)."""
        return sum(len(routes) for routes in self._adj.values())

    def out_degree(self, airport_id: str) -> int:
        """Return the number of outgoing routes from an airport."""
        if airport_id not in self._nodes:
            raise KeyError(f"Airport '{airport_id}' not found in the graph.")
        return len(self._adj[airport_id])

    def in_degree(self, airport_id: str) -> int:
        """Return the number of routes arriving at an airport."""
        if airport_id not in self._nodes:
            raise KeyError(f"Airport '{airport_id}' not found in the graph.")
        return sum(
            1
            for routes in self._adj.values()
            for r in routes
            if r.destino == airport_id
        )

    # ------------------------------------------------------------------
    # Route blocking (R4 — Interruptions)
    # ------------------------------------------------------------------

    def block_route(self, origen: str, destino: str) -> None:
        """
        Block the route from origen to destino.

        The edge is NOT removed from the adjacency list; it is only
        flagged so that get_neighbors() skips it. This keeps the route
        visible on the UI (highlighted in a different colour) and allows
        it to be restored without re-inserting data.

        Args:
            origen:  IATA code of the route's origin airport.
            destino: IATA code of the route's destination airport.

        Raises:
            KeyError: If the route does not exist.
        """
        route = self.get_route(origen, destino)
        if route is None:
            raise KeyError(f"Route '{origen}' → '{destino}' not found in the graph.")
        route.bloquear()

    def unblock_route(self, origen: str, destino: str) -> None:
        """
        Restore a previously blocked route.

        Raises:
            KeyError: If the route does not exist.
        """
        route = self.get_route(origen, destino)
        if route is None:
            raise KeyError(f"Route '{origen}' → '{destino}' not found in the graph.")
        route.desbloquear()

    def get_blocked_routes(self) -> list[Route]:
        """Return all currently blocked routes (for UI highlighting)."""
        return [r for r in self.get_all_edges() if r.bloqueada]

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AdjacencyGraph("
            f"airports={self.node_count()}, "
            f"routes={self.edge_count()}, "
            f"blocked={len(self.get_blocked_routes())})"
        )

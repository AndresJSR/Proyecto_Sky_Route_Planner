"""Dijkstra-based route search placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ..graph import AirRouteGraph


@dataclass(slots=True)
class DijkstraAlgorithm:
    """Skeleton for the shortest path algorithm."""

    graph: AirRouteGraph

    def find_shortest_path(self, origin_code: str, destination_code: str) -> list[str]:
        """Return the route nodes for the shortest path.

        TODO: Implement the full Dijkstra algorithm.
        """
        raise NotImplementedError("DijkstraAlgorithm.find_shortest_path is not implemented yet.")

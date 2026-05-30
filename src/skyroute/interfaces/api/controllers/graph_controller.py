"""Graph controller placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ....application.services import GraphService


@dataclass(slots=True)
class GraphController:
    """Placeholder controller for graph operations."""

    graph_service: GraphService

    def get_graph_summary(self) -> dict[str, int]:
        """Return a minimal graph summary."""
        graph = self.graph_service.graph
        return {
            "airports": len(graph.get_all_airports()),
            "routes": len(graph.get_all_routes()),
        }

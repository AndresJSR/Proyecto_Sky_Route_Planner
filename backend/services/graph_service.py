# Stub for Persona 2 — Graph service (query helpers)
# TODO: Implement node/edge query helpers used by the API and planners
from graph.adjacency_graph import AdjacencyGraph


class GraphService:
    """Exposes read-only query operations on the AdjacencyGraph."""

    def __init__(self, graph: AdjacencyGraph) -> None:
        self.graph = graph

    def obtener_info_aeropuerto(self, airport_id: str) -> dict:
        """Return full info dict for a given airport node."""
        raise NotImplementedError

    def listar_aeropuertos(self, solo_hubs: bool = False) -> list[dict]:
        """Return all airports, optionally filtered to hubs only."""
        raise NotImplementedError

    def listar_rutas(self, include_blocked: bool = False) -> list[dict]:
        """Return all routes, optionally including blocked ones."""
        raise NotImplementedError

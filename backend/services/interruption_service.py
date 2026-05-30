# Stub for Persona 3 — Interruption service
# TODO: Implement route blocking, traveler redirection, and itinerary recalculation
from graph.adjacency_graph import AdjacencyGraph


class InterruptionService:
    """Handles real-time route interruptions and itinerary recalculation."""

    def __init__(self, graph: AdjacencyGraph) -> None:
        self.graph = graph

    def bloquear_ruta(self, origen: str, destino: str) -> None:
        """Block a route and trigger rerouting if the traveler is on it."""
        self.graph.block_route(origen, destino)

    def desbloquear_ruta(self, origen: str, destino: str) -> None:
        """Restore a previously blocked route."""
        self.graph.unblock_route(origen, destino)

    def recalcular_itinerario(self, estado_viajero: dict) -> dict:
        """Recalculate the best available itinerary after an interruption."""
        raise NotImplementedError

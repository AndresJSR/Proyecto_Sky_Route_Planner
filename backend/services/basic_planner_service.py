# Stub for Persona 2 — Basic planner service
# TODO: Wire Dijkstra and backtracking into user-facing route proposals
from graph.adjacency_graph import AdjacencyGraph


class BasicPlannerService:
    """Proposes itineraries using Dijkstra and DFS/backtracking algorithms."""

    def __init__(self, graph: AdjacencyGraph, config: dict) -> None:
        self.graph = graph
        self.config = config

    def calcular_ruta_optima(
        self,
        origen: str,
        destino: str,
        criterio: str,
        incluir_secundarios: bool = True,
        tipos_transporte: list[str] | None = None,
    ) -> dict:
        """
        Calculate the best route between two airports by the given criterion.

        Args:
            criterio: 'costo' | 'tiempo' | 'distancia'
        """
        raise NotImplementedError

    def proponer_itinerarios(
        self,
        origen: str,
        presupuesto: float,
        tiempo_disponible_horas: float,
        incluir_secundarios: bool = True,
        tipos_transporte: list[str] | None = None,
    ) -> dict:
        """
        Propose two itineraries:
          a) Max destinations within budget.
          b) Max destinations within available time.
        """
        raise NotImplementedError

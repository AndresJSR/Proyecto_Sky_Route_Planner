# Stub for Persona 2 — DFS/backtracking with constraints
# TODO: Implement max-destination search with budget and time constraints
from graph.adjacency_graph import AdjacencyGraph


def max_destinos_presupuesto(
    graph: AdjacencyGraph,
    origen: str,
    presupuesto: float,
    incluir_secundarios: bool = True,
    tipos_transporte: list[str] | None = None,
) -> dict:
    """
    Find the itinerary that visits the most destinations without exceeding budget.
    Uses DFS with backtracking.
    """
    raise NotImplementedError


def max_destinos_tiempo(
    graph: AdjacencyGraph,
    origen: str,
    tiempo_disponible_min: float,
    incluir_secundarios: bool = True,
    tipos_transporte: list[str] | None = None,
) -> dict:
    """
    Find the itinerary that visits the most destinations in the least time
    without exceeding the available time budget.
    Uses DFS with backtracking.
    """
    raise NotImplementedError

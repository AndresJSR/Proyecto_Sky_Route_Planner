# Stub for Persona 2 — Dijkstra algorithms
# TODO: Implement Dijkstra by cost, time and distance
from graph.adjacency_graph import AdjacencyGraph


def dijkstra_costo(graph: AdjacencyGraph, origen: str, destino: str) -> dict:
    """Shortest path from origen to destino minimising total cost (USD)."""
    raise NotImplementedError


def dijkstra_tiempo(graph: AdjacencyGraph, origen: str, destino: str) -> dict:
    """Shortest path from origen to destino minimising total flight time (min)."""
    raise NotImplementedError


def dijkstra_distancia(graph: AdjacencyGraph, origen: str, destino: str) -> dict:
    """Shortest path from origen to destino minimising total distance (km)."""
    raise NotImplementedError

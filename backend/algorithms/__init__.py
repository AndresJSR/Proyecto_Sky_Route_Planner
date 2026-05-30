# Public API of the algorithms package.
#
# Dijkstra variants (point-to-point shortest path)
from algorithms.dijkstra import dijkstra_costo, dijkstra_tiempo, dijkstra_distancia

# Backtracking variants (max-destination itineraries under constraints)
from algorithms.backtracking import max_destinos_presupuesto, max_destinos_tiempo

__all__ = [
    "dijkstra_costo",
    "dijkstra_tiempo",
    "dijkstra_distancia",
    "max_destinos_presupuesto",
    "max_destinos_tiempo",
]

"""
Dijkstra's shortest-path algorithm — three variants (Persona 2, R2).

Justification for Dijkstra
--------------------------
The flight network is a directed weighted graph where all edge weights
(cost, time, distance) are strictly non-negative. Dijkstra's algorithm
is the correct choice for this case: it guarantees the shortest path in
O((V + E) log V) using a min-heap, without the O(V·E) overhead of
Bellman-Ford, which would be wasteful on a graph with only positive weights.

Three optimisation criteria are provided as independent public functions:
    * dijkstra_costo      — minimise total flight cost (USD).
    * dijkstra_tiempo     — minimise total airborne time (min).
    * dijkstra_distancia  — minimise total distance flown (km).

Each variant selects the best available aircraft per leg according to the
active criterion (cheapest / fastest). Distance is aircraft-independent,
so the first available aircraft is recorded for reporting purposes only.

Return format (all three functions)
------------------------------------
On success:
    {
        "ruta":               ["BOG", "MDE", "CTG"],   # ordered IATA codes
        "tramos": [
            {
                "origen":       "BOG",
                "destino":      "MDE",
                "distancia_km": 240.0,
                "aeronave":     "Avión Regional",
                "costo_usd":    60.0,
                "tiempo_min":   264.0,
            },
            ...
        ],
        "total_distancia_km": 790.0,
        "total_costo_usd":    ...,
        "total_tiempo_min":   ...,
    }

When no path exists: returns None.

"""

from __future__ import annotations

import heapq
from typing import Callable

from domain.models.aircraft import Aircraft
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from algorithms.shared import build_aircraft_registry, build_result

# Weight function: (Route, registry) → (metric_value, chosen_aircraft_name)
_WeightFn = Callable[[Route, dict[str, Aircraft]], tuple[float, str]]


# ──────────────────────────────────────────────────────────────────────────────
# Weight functions — one per optimisation criterion
# ──────────────────────────────────────────────────────────────────────────────

def _weight_costo(route: Route, registry: dict[str, Aircraft]) -> tuple[float, str]:
    """Return (min_cost_usd, best_aircraft_name) for a route."""
    if route.es_subsidiada:
        return 0.0, route.aeronaves[0]
    best_cost = float("inf")
    best_name = route.aeronaves[0]
    for nombre in route.aeronaves:
        if nombre in registry:
            c = registry[nombre].calcular_costo(route.distancia_km)
            if c < best_cost:
                best_cost = c
                best_name = nombre
    return best_cost, best_name


def _weight_tiempo(route: Route, registry: dict[str, Aircraft]) -> tuple[float, str]:
    """Return (min_time_min, fastest_aircraft_name) for a route."""
    best_time = float("inf")
    best_name = route.aeronaves[0]
    for nombre in route.aeronaves:
        if nombre in registry:
            t = registry[nombre].calcular_tiempo(route.distancia_km)
            if t < best_time:
                best_time = t
                best_name = nombre
    return best_time, best_name


def _weight_distancia(route: Route, _registry: dict[str, Aircraft]) -> tuple[float, str]:
    """Return (distancia_km, first_aircraft_name) for a route."""
    return route.distancia_km, route.aeronaves[0]


# ──────────────────────────────────────────────────────────────────────────────
# Generic Dijkstra core
# ──────────────────────────────────────────────────────────────────────────────

def _dijkstra(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    weight_fn: _WeightFn,
    aircraft_registry: dict[str, Aircraft],
) -> dict | None:
    """
    Core Dijkstra implementation using a binary min-heap (heapq).

    Algorithm steps
    ---------------
    1. Initialise every node's tentative distance to +∞ except the
       source (dist = 0).
    2. Push (0, origen) onto the min-heap.
    3. Pop the node u with the smallest tentative distance.
       - If u is already settled (visited), skip it.
       - Mark u as settled.
       - If u == destino, stop early.
    4. For each outgoing edge u→v (blocked routes are already excluded
       by get_neighbors()):
       - Compute candidate = dist[u] + weight_fn(edge).
       - If candidate < dist[v], relax: update dist[v] and prev[v],
         then push (candidate, v) onto the heap.
    5. If destino was never settled, return None (no path).
    6. Reconstruct the path by walking prev[] from destino back to
       origen, then reverse for correct order.

    Complexity: O((V + E) log V) due to the min-heap.

    Args:
        graph:             The flight network graph.
        origen:            IATA code of the departure airport.
        destino:           IATA code of the arrival airport.
        weight_fn:         Function that returns (weight, aircraft_name)
                           for a given route and aircraft registry.
        aircraft_registry: Dict mapping aircraft type name → Aircraft.

    Returns:
        Result dict on success, or None when no path exists.

    Raises:
        KeyError: If origen or destino are not in the graph.
    """
    if not graph.has_node(origen):
        raise KeyError(f"Origin airport '{origen}' not found in the graph.")
    if not graph.has_node(destino):
        raise KeyError(f"Destination airport '{destino}' not found in the graph.")

    # dist[node_id] = best accumulated weight found so far
    dist: dict[str, float] = {node.id: float("inf") for node in graph.get_all_nodes()}
    dist[origen] = 0.0

    # prev[node_id] = (parent_id, Route, aircraft_name) used to reach this node
    prev: dict[str, tuple[str, Route, str] | None] = {
        node.id: None for node in graph.get_all_nodes()
    }

    # Min-heap entries: (accumulated_weight, node_id)
    heap: list[tuple[float, str]] = [(0.0, origen)]
    visited: set[str] = set()

    while heap:
        current_dist, current = heapq.heappop(heap)

        # A node may appear multiple times in the heap with outdated distances;
        # skip if already settled with a better value.
        if current in visited:
            continue
        visited.add(current)

        if current == destino:
            break

        for route in graph.get_neighbors(current):
            neighbour = route.destino
            if neighbour in visited:
                continue
            weight, aircraft_name = weight_fn(route, aircraft_registry)
            candidate = current_dist + weight
            if candidate < dist[neighbour]:
                dist[neighbour] = candidate
                prev[neighbour] = (current, route, aircraft_name)
                heapq.heappush(heap, (candidate, neighbour))

    # Destination was never reached
    if dist[destino] == float("inf"):
        return None

    # Reconstruct path walking prev[] backwards from destino to origen
    path_nodes: list[str] = []
    tramos: list[dict] = []
    node = destino

    while node != origen:
        parent, route, aircraft_name = prev[node]
        ac = aircraft_registry.get(aircraft_name)
        costo_tramo  = ac.calcular_costo(route.distancia_km)  if ac else 0.0
        tiempo_tramo = ac.calcular_tiempo(route.distancia_km) if ac else 0.0
        tramos.append({
            "origen":       route.origen,
            "destino":      route.destino,
            "distancia_km": route.distancia_km,
            "aeronave":     aircraft_name,
            "costo_usd":    0.0 if route.es_subsidiada else costo_tramo,
            "tiempo_min":   tiempo_tramo,
        })
        path_nodes.append(node)
        node = parent

    path_nodes.append(origen)
    path_nodes.reverse()
    tramos.reverse()

    return build_result(path_nodes, tramos)


# ──────────────────────────────────────────────────────────────────────────────
# Public API — three Dijkstra variants
# ──────────────────────────────────────────────────────────────────────────────

def dijkstra_costo(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
) -> dict | None:
    """
    Shortest path from origen to destino minimising total cost (USD).

    Per leg, the aircraft with the lowest costo_km is chosen.
    Subsidised routes (costo_base == 0) contribute $0 to the total.

    Args:
        graph:             The flight network graph.
        origen:            IATA code of the departure airport.
        destino:           IATA code of the arrival airport.
        aircraft_registry: Optional dict of Aircraft objects with operative
                           rates (e.g. from JSONLoader config overrides).
                           Falls back to DEFAULT_AIRCRAFT rates if None.

    Returns:
        Result dict with 'ruta', 'tramos', 'total_distancia_km',
        'total_costo_usd', 'total_tiempo_min'; or None if unreachable.
    """
    registry = aircraft_registry or build_aircraft_registry()
    return _dijkstra(graph, origen, destino, _weight_costo, registry)


def dijkstra_tiempo(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
) -> dict | None:
    """
    Shortest path from origen to destino minimising total flight time (min).

    Per leg, the aircraft with the lowest tiempo_km is chosen.

    Args:
        graph:             The flight network graph.
        origen:            IATA code of the departure airport.
        destino:           IATA code of the arrival airport.
        aircraft_registry: Optional dict of Aircraft objects with operative
                           rates. Falls back to DEFAULT_AIRCRAFT rates if None.

    Returns:
        Result dict with 'ruta', 'tramos', totals; or None if unreachable.
    """
    registry = aircraft_registry or build_aircraft_registry()
    return _dijkstra(graph, origen, destino, _weight_tiempo, registry)


def dijkstra_distancia(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
) -> dict | None:
    """
    Shortest path from origen to destino minimising total distance (km).

    Aircraft type does not influence the distance weight; the first
    available aircraft on each leg is recorded for reporting only.

    Args:
        graph:             The flight network graph.
        origen:            IATA code of the departure airport.
        destino:           IATA code of the arrival airport.
        aircraft_registry: Optional dict of Aircraft objects with operative
                           rates. Falls back to DEFAULT_AIRCRAFT rates if None.

    Returns:
        Result dict with 'ruta', 'tramos', totals; or None if unreachable.
    """
    registry = aircraft_registry or build_aircraft_registry()
    return _dijkstra(graph, origen, destino, _weight_distancia, registry)

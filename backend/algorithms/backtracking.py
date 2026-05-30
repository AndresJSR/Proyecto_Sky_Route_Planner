"""
Backtracking algorithms — DFS with constraint pruning.

Justification for DFS / Backtracking
-------------------------------------
Finding the itinerary that maximises the number of visited destinations
under a budget or time constraint is NP-hard in the general case (it
reduces to the constrained Hamiltonian-path problem). For the project
network size (≤ 29 airports), exhaustive DFS with constraint-based
pruning is the correct and project-specified approach:

  * A route is added to the current path only when its accumulated
    cost/time does not exceed the remaining budget/time  →  pruning.
  * When no valid extension exists the algorithm backtracks one step
    and tries the next alternative.
  * The globally optimal solution (maximum destinations) is guaranteed
    because the full feasible state-space is explored.

Complexity: O(V!) worst case, but early pruning makes it practical for
small networks.  The project specification explicitly calls for this
approach.

Return format (both functions)
-------------------------------
On success (including the trivial case where no route fits the constraint):

    {
        "ruta":               ["BOG", "MDE", "CTG"],
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

When no departure is possible (all first legs exceed the constraint),
the origin-only result is returned with empty tramos and zero totals.

"""

from __future__ import annotations

from typing import Callable

from domain.models.aircraft import Aircraft
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from algorithms.shared import build_aircraft_registry, filter_valid_routes, build_result

# Weight function: (Route, registry) → (peso, aeronave, costo_usd, tiempo_min)
_BacktrackWeightFn = Callable[[Route, dict[str, Aircraft]], tuple[float, str, float, float]]


# ──────────────────────────────────────────────────────────────────────────────
# Weight functions
# ──────────────────────────────────────────────────────────────────────────────

def _best_cost_for_leg(
    route: Route,
    registry: dict[str, Aircraft],
) -> tuple[float, str, float, float]:
    """Return (min_cost, aircraft_name, min_cost, flight_time) for a route."""
    if route.es_subsidiada:
        for name in route.aeronaves:
            if name in registry:
                tiempo = registry[name].calcular_tiempo(route.distancia_km)
                return 0.0, name, 0.0, tiempo
    best_cost = float("inf")
    best_name = ""
    for name in route.aeronaves:
        if name in registry:
            c = registry[name].calcular_costo(route.distancia_km)
            if c < best_cost:
                best_cost = c
                best_name = name
    tiempo = registry[best_name].calcular_tiempo(route.distancia_km) if best_name else 0.0
    return best_cost, best_name, best_cost, tiempo


def _best_time_for_leg(
    route: Route,
    registry: dict[str, Aircraft],
) -> tuple[float, str, float, float]:
    """Return (min_time, aircraft_name, cost, min_time) for a route."""
    best_time = float("inf")
    best_name = ""
    for name in route.aeronaves:
        if name in registry:
            t = registry[name].calcular_tiempo(route.distancia_km)
            if t < best_time:
                best_time = t
                best_name = name
    costo = 0.0 if route.es_subsidiada else (
        registry[best_name].calcular_costo(route.distancia_km) if best_name else 0.0
    )
    return best_time, best_name, costo, best_time


# ──────────────────────────────────────────────────────────────────────────────
# Generic DFS core
# ──────────────────────────────────────────────────────────────────────────────

def _dfs_max_destinos(
    graph: AdjacencyGraph,
    origen: str,
    registry: dict[str, Aircraft],
    incluir_secundarios: bool,
    weight_fn: _BacktrackWeightFn,
    constraint_fn: Callable[[float, float], bool],
    best: list[dict],
) -> None:
    """
    Generic DFS that maximises visited destinations under a constraint.

    weight_fn returns (peso, aeronave, costo_usd, tiempo_min) for a leg.
    constraint_fn(accumulated, peso) returns True when the leg is feasible.

    Args:
        graph:               Flight network graph.
        origen:              IATA code of the departure airport.
        registry:            Allowed aircraft registry.
        incluir_secundarios: When False, only hub airports are visited.
        weight_fn:           Computes all leg metrics given a route and registry.
        constraint_fn:       Returns True when the leg fits within the remaining
                             constraint budget.
        best:                Single-element list holding the current best result
                             (mutable reference so nested calls can update it).
    """

    def dfs(
        current: str,
        visited: set[str],
        path: list[str],
        tramos: list[dict],
        acumulado: float,
    ) -> None:
        # Update best whenever the current path visits more airports.
        if len(path) > len(best[0]["ruta"]):
            best[0] = build_result(path, tramos)

        for route in filter_valid_routes(graph, current, registry, incluir_secundarios):
            dest = route.destino
            if dest in visited:
                continue

            peso, aeronave, costo_usd, tiempo_min = weight_fn(route, registry)

            # Pruning: skip branches that violate the constraint.
            if not constraint_fn(acumulado, peso):
                continue

            tramo = {
                "origen":       current,
                "destino":      dest,
                "distancia_km": route.distancia_km,
                "aeronave":     aeronave,
                "costo_usd":    costo_usd,
                "tiempo_min":   tiempo_min,
            }

            visited.add(dest)
            path.append(dest)
            tramos.append(tramo)

            dfs(dest, visited, path, tramos, acumulado + peso)

            # Backtrack — restore state for the next candidate.
            visited.discard(dest)
            path.pop()
            tramos.pop()

    dfs(origen, {origen}, [origen], [], 0.0)


# ──────────────────────────────────────────────────────────────────────────────
# Public functions
# ──────────────────────────────────────────────────────────────────────────────

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

    For each leg the aircraft that minimises cost is chosen (CostLegEvaluator).
    A branch is explored only when the accumulated cost does not exceed the
    budget (constraint pruning).

    Args:
        graph:               Flight network graph.
        origen:              IATA code of the departure airport.
        presupuesto:         Total available budget in USD.
        incluir_secundarios: When False, only hub airports are visited.
        tipos_transporte:    Allowed aircraft type names; None means all types.

    Returns:
        Result dict with ruta, tramos and accumulated totals.
    """
    registry = build_aircraft_registry(tipos_transporte)
    best: list[dict] = [build_result([origen], [])]

    _dfs_max_destinos(
        graph=graph,
        origen=origen,
        registry=registry,
        incluir_secundarios=incluir_secundarios,
        weight_fn=_best_cost_for_leg,
        constraint_fn=lambda acum, peso: acum + peso <= presupuesto,
        best=best,
    )
    return best[0]


def max_destinos_tiempo(
    graph: AdjacencyGraph,
    origen: str,
    tiempo_disponible_min: float,
    incluir_secundarios: bool = True,
    tipos_transporte: list[str] | None = None,
) -> dict:
    """
    Find the itinerary that visits the most destinations without exceeding
    the available time budget.
    Uses DFS with backtracking.

    For each leg the fastest aircraft is chosen (TimeLegEvaluator).
    A branch is explored only when the accumulated flight time does not
    exceed the time limit (constraint pruning).

    Args:
        graph:                  Flight network graph.
        origen:                 IATA code of the departure airport.
        tiempo_disponible_min:  Total available time in minutes.
        incluir_secundarios:    When False, only hub airports are visited.
        tipos_transporte:       Allowed aircraft type names; None means all types.

    Returns:
        Result dict with ruta, tramos and accumulated totals.
    """
    registry = build_aircraft_registry(tipos_transporte)
    best: list[dict] = [build_result([origen], [])]

    _dfs_max_destinos(
        graph=graph,
        origen=origen,
        registry=registry,
        incluir_secundarios=incluir_secundarios,
        weight_fn=_best_time_for_leg,
        constraint_fn=lambda acum, peso: acum + peso <= tiempo_disponible_min,
        best=best,
    )
    return best[0]

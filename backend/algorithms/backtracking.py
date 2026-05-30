"""
Backtracking algorithms for constrained itinerary planning.

Responsibility
--------------
This module implements DFS with backtracking and constraint pruning to find
the itinerary that visits the maximum number of destinations without exceeding
a hard budget or time limit.

This is different from Dijkstra:
    - Dijkstra minimizes a path between one origin and one destination.
    - Backtracking explores feasible paths to maximize the number of visited
      airports under a constraint.

Justification
-------------
The requirement "visit the greatest number of destinations without exceeding
budget/time and without repeating airports" is a constrained path search
problem. Dijkstra is not enough because the objective is not only to minimize
one accumulated weight between two fixed nodes, but to maximize coverage.

DFS with backtracking is appropriate for the project because:
    - It explores feasible paths.
    - It prunes branches that exceed the constraint.
    - It prevents repeated airports using a visited set.
    - It guarantees the best feasible result for small/medium project graphs.

Worst-case complexity is exponential, but constraint pruning keeps it practical
for the expected project size.
"""

from __future__ import annotations

from typing import Any, Literal

from algorithms.shared import (
    build_aircraft_registry,
    build_leg,
    build_result,
    filter_valid_routes,
    get_route_weight,
    select_best_aircraft,
)
from domain.models.aircraft import Aircraft
from graph.adjacency_graph import AdjacencyGraph


ConstraintMode = Literal["cost", "time"]


def _is_better_result(
    candidate_path: list[str],
    candidate_total: float,
    best_path: list[str],
    best_total: float,
) -> bool:
    """
    Decide if a candidate path is better than the current best path.

    Priority:
        1. Visit more destinations.
        2. If tied, use less accumulated cost/time.

    Args:
        candidate_path: Current DFS path.
        candidate_total: Current accumulated constraint value.
        best_path: Best path found so far.
        best_total: Best accumulated constraint value found so far.

    Returns:
        True if candidate should replace the current best.
    """
    candidate_destinations = max(len(candidate_path) - 1, 0)
    best_destinations = max(len(best_path) - 1, 0)

    if candidate_destinations > best_destinations:
        return True

    if candidate_destinations == best_destinations and candidate_total < best_total:
        return True

    return False


def _resolve_registry(
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
) -> dict[str, Aircraft]:
    """
    Resolve the aircraft registry used by backtracking.

    Args:
        aircraft_registry: Optional registry created from JSON configuration.
        tipos_transporte: Optional list of aircraft types allowed by the user.

    Returns:
        Filtered aircraft registry.
    """
    if aircraft_registry is None:
        return build_aircraft_registry(tipos_transporte)

    if tipos_transporte is None:
        return aircraft_registry

    return {
        name: aircraft
        for name, aircraft in aircraft_registry.items()
        if name in tipos_transporte
    }


def _max_destinations_with_constraint(
    graph: AdjacencyGraph,
    origen: str,
    limit: float,
    mode: ConstraintMode,
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
    include_secondary: bool = True,
) -> dict[str, Any]:
    """
    Generic DFS with backtracking for budget or time constrained planning.

    Args:
        graph: Flight network graph.
        origen: Origin airport IATA code.
        limit: Maximum allowed accumulated cost or time.
        mode: Constraint mode, either 'cost' or 'time'.
        aircraft_registry: Optional aircraft registry with operative rates.
        tipos_transporte: Optional list of allowed aircraft type names.
        include_secondary: When False, secondary airports are excluded.

    Returns:
        Standard result dictionary.
    """
    if mode not in {"cost", "time"}:
        raise ValueError("Backtracking mode must be either 'cost' or 'time'.")

    if limit < 0:
        raise ValueError("The constraint limit cannot be negative.")

    if not graph.has_node(origen):
        raise KeyError(f"Origin airport '{origen}' not found in the graph.")

    registry = _resolve_registry(
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
    )

    if not registry:
        return build_result(path=[origen], tramos=[])

    best: dict[str, Any] = {
        "path": [origen],
        "legs": [],
        "total": 0.0,
    }

    def dfs(
        current_airport: str,
        visited: set[str],
        current_path: list[str],
        current_legs: list[dict[str, Any]],
        accumulated: float,
    ) -> None:
        nonlocal best

        if _is_better_result(
            candidate_path=current_path,
            candidate_total=accumulated,
            best_path=best["path"],
            best_total=best["total"],
        ):
            best = {
                "path": list(current_path),
                "legs": list(current_legs),
                "total": accumulated,
            }

        valid_routes = filter_valid_routes(
            graph=graph,
            airport_id=current_airport,
            registry=registry,
            include_secondary=include_secondary,
        )

        for route in valid_routes:
            next_airport = route.destino

            if next_airport in visited:
                continue

            aircraft = select_best_aircraft(
                route=route,
                registry=registry,
                criterion=mode,
            )

            if aircraft is None:
                continue

            weight = get_route_weight(
                route=route,
                aircraft=aircraft,
                criterion=mode,
            )

            new_accumulated = accumulated + weight

            # Constraint pruning.
            if new_accumulated > limit:
                continue

            leg = build_leg(route=route, aircraft=aircraft)

            visited.add(next_airport)
            current_path.append(next_airport)
            current_legs.append(leg)

            dfs(
                current_airport=next_airport,
                visited=visited,
                current_path=current_path,
                current_legs=current_legs,
                accumulated=new_accumulated,
            )

            # Backtrack.
            visited.remove(next_airport)
            current_path.pop()
            current_legs.pop()

    dfs(
        current_airport=origen,
        visited={origen},
        current_path=[origen],
        current_legs=[],
        accumulated=0.0,
    )

    return build_result(
        path=best["path"],
        tramos=best["legs"],
    )


def max_destinos_presupuesto(
    graph: AdjacencyGraph,
    origen: str,
    presupuesto: float,
    incluir_secundarios: bool = True,
    tipos_transporte: list[str] | None = None,
    aircraft_registry: dict[str, Aircraft] | None = None,
) -> dict[str, Any]:
    """
    Find the itinerary that visits the most destinations under a budget limit.

    Optimization logic:
        1. Maximize number of visited destinations.
        2. If there is a tie, choose the itinerary with the lowest total cost.

    Args:
        graph: Flight network graph.
        origen: Origin airport IATA code.
        presupuesto: Maximum available budget in USD.
        incluir_secundarios: When False, secondary airports are excluded.
        tipos_transporte: Optional list of allowed aircraft types.
        aircraft_registry: Optional aircraft registry with JSON override rates.

    Returns:
        Standard result dictionary.
    """
    return _max_destinations_with_constraint(
        graph=graph,
        origen=origen,
        limit=presupuesto,
        mode="cost",
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
        include_secondary=incluir_secundarios,
    )


def max_destinos_tiempo(
    graph: AdjacencyGraph,
    origen: str,
    tiempo_disponible_min: float,
    incluir_secundarios: bool = True,
    tipos_transporte: list[str] | None = None,
    aircraft_registry: dict[str, Aircraft] | None = None,
) -> dict[str, Any]:
    """
    Find the itinerary that visits the most destinations under a time limit.

    Optimization logic:
        1. Maximize number of visited destinations.
        2. If there is a tie, choose the itinerary with the lowest total time.

    Args:
        graph: Flight network graph.
        origen: Origin airport IATA code.
        tiempo_disponible_min: Maximum available flight time in minutes.
        incluir_secundarios: When False, secondary airports are excluded.
        tipos_transporte: Optional list of allowed aircraft types.
        aircraft_registry: Optional aircraft registry with JSON override rates.

    Returns:
        Standard result dictionary.
    """
    return _max_destinations_with_constraint(
        graph=graph,
        origen=origen,
        limit=tiempo_disponible_min,
        mode="time",
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
        include_secondary=incluir_secundarios,
    )
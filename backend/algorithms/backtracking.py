"""
Backtracking algorithms for constrained itinerary planning.

Responsibility
--------------
This module implements DFS with backtracking and constraint pruning to find
the itinerary that visits the maximum number of destinations without exceeding
hard budget and/or time limits.

This is different from Dijkstra:
    - Dijkstra minimizes a path between one origin and one destination.
    - Backtracking explores feasible paths to maximize the number of visited
      airports under constraints.

Justification
-------------
The requirement "visit the greatest number of destinations without exceeding
budget/time and without repeating airports" is a constrained path search
problem. Dijkstra is not enough because the objective is not only to minimize
one accumulated weight between two fixed nodes, but to maximize coverage.

DFS with backtracking is appropriate for the project because:
    - It explores feasible paths.
    - It prunes branches that exceed hard constraints.
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
    get_available_aircraft_for_route,
)
from domain.models.aircraft import Aircraft
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph


ConstraintMode = Literal["cost", "time"]


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


def _validate_limits(
    budget_limit: float | None,
    time_limit: float | None,
) -> None:
    """
    Validate budget and time limits.

    At least one limit must be provided. When both are provided, both are
    treated as hard constraints.
    """
    if budget_limit is None and time_limit is None:
        raise ValueError("At least one constraint limit must be provided.")

    if budget_limit is not None and budget_limit < 0:
        raise ValueError("The budget limit cannot be negative.")

    if time_limit is not None and time_limit < 0:
        raise ValueError("The time limit cannot be negative.")


def _sort_aircraft_candidates(
    route: Route,
    registry: dict[str, Aircraft],
    tie_breaker: ConstraintMode,
) -> list[Aircraft]:
    """
    Return aircraft candidates sorted according to the optimization preference.

    Even when one criterion is preferred, all available aircraft are considered.
    This is important when budget and time are both hard constraints: the
    cheapest aircraft may be too slow, or the fastest one may be too expensive.
    """
    candidates = get_available_aircraft_for_route(route, registry)

    if tie_breaker == "cost":
        return sorted(
            candidates,
            key=lambda aircraft: (
                build_leg(route, aircraft)["costo_usd"],
                build_leg(route, aircraft)["tiempo_min"],
            ),
        )

    if tie_breaker == "time":
        return sorted(
            candidates,
            key=lambda aircraft: (
                build_leg(route, aircraft)["tiempo_min"],
                build_leg(route, aircraft)["costo_usd"],
            ),
        )

    raise ValueError("Tie breaker must be either 'cost' or 'time'.")


def _is_better_result(
    candidate_path: list[str],
    candidate_cost: float,
    candidate_time: float,
    best_path: list[str],
    best_cost: float,
    best_time: float,
    tie_breaker: ConstraintMode,
) -> bool:
    """
    Decide if a candidate path is better than the current best path.

    Priority:
        1. Visit more destinations.
        2. If tied, use the selected tie breaker:
            - cost: lower total cost.
            - time: lower total time.
        3. If still tied, use the secondary metric.
    """
    candidate_destinations = max(len(candidate_path) - 1, 0)
    best_destinations = max(len(best_path) - 1, 0)

    if candidate_destinations > best_destinations:
        return True

    if candidate_destinations < best_destinations:
        return False

    if tie_breaker == "cost":
        if candidate_cost < best_cost:
            return True
        if candidate_cost == best_cost and candidate_time < best_time:
            return True
        return False

    if tie_breaker == "time":
        if candidate_time < best_time:
            return True
        if candidate_time == best_time and candidate_cost < best_cost:
            return True
        return False

    raise ValueError("Tie breaker must be either 'cost' or 'time'.")


def _max_destinations_with_limits(
    graph: AdjacencyGraph,
    origen: str,
    budget_limit: float | None,
    time_limit: float | None,
    tie_breaker: ConstraintMode,
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
    include_secondary: bool = True,
) -> dict[str, Any]:
    """
    Generic DFS with backtracking for budget and/or time constrained planning.

    Args:
        graph: Flight network graph.
        origen: Origin airport IATA code.
        budget_limit: Maximum allowed cost in USD. None means no budget limit.
        time_limit: Maximum allowed time in minutes. None means no time limit.
        tie_breaker: Optimization preference for equal destination counts.
        aircraft_registry: Optional aircraft registry with operative rates.
        tipos_transporte: Optional list of allowed aircraft type names.
        include_secondary: When False, secondary airports are excluded.

    Returns:
        Standard result dictionary.
    """
    if tie_breaker not in {"cost", "time"}:
        raise ValueError("Tie breaker must be either 'cost' or 'time'.")

    _validate_limits(budget_limit=budget_limit, time_limit=time_limit)

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
        "total_cost": 0.0,
        "total_time": 0.0,
    }

    def dfs(
        current_airport: str,
        visited: set[str],
        current_path: list[str],
        current_legs: list[dict[str, Any]],
        accumulated_cost: float,
        accumulated_time: float,
    ) -> None:
        nonlocal best

        if _is_better_result(
            candidate_path=current_path,
            candidate_cost=accumulated_cost,
            candidate_time=accumulated_time,
            best_path=best["path"],
            best_cost=best["total_cost"],
            best_time=best["total_time"],
            tie_breaker=tie_breaker,
        ):
            best = {
                "path": list(current_path),
                "legs": list(current_legs),
                "total_cost": accumulated_cost,
                "total_time": accumulated_time,
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

            aircraft_candidates = _sort_aircraft_candidates(
                route=route,
                registry=registry,
                tie_breaker=tie_breaker,
            )

            for aircraft in aircraft_candidates:
                leg = build_leg(route=route, aircraft=aircraft)

                new_cost = accumulated_cost + float(leg["costo_usd"])
                new_time = accumulated_time + float(leg["tiempo_min"])

                # Hard-constraint pruning.
                if budget_limit is not None and new_cost > budget_limit:
                    continue

                if time_limit is not None and new_time > time_limit:
                    continue

                visited.add(next_airport)
                current_path.append(next_airport)
                current_legs.append(leg)

                dfs(
                    current_airport=next_airport,
                    visited=visited,
                    current_path=current_path,
                    current_legs=current_legs,
                    accumulated_cost=new_cost,
                    accumulated_time=new_time,
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
        accumulated_cost=0.0,
        accumulated_time=0.0,
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

    This function keeps backward compatibility with previous tests and uses
    only budget as a hard constraint.

    Optimization logic:
        1. Maximize number of visited destinations.
        2. If there is a tie, choose the itinerary with the lowest total cost.
    """
    return _max_destinations_with_limits(
        graph=graph,
        origen=origen,
        budget_limit=presupuesto,
        time_limit=None,
        tie_breaker="cost",
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

    This function keeps backward compatibility with previous tests and uses
    only time as a hard constraint.

    Optimization logic:
        1. Maximize number of visited destinations.
        2. If there is a tie, choose the itinerary with the lowest total time.
    """
    return _max_destinations_with_limits(
        graph=graph,
        origen=origen,
        budget_limit=None,
        time_limit=tiempo_disponible_min,
        tie_breaker="time",
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
        include_secondary=incluir_secundarios,
    )


def max_destinos_presupuesto_y_tiempo(
    graph: AdjacencyGraph,
    origen: str,
    presupuesto: float,
    tiempo_disponible_min: float,
    criterio_desempate: ConstraintMode,
    incluir_secundarios: bool = True,
    tipos_transporte: list[str] | None = None,
    aircraft_registry: dict[str, Aircraft] | None = None,
) -> dict[str, Any]:
    """
    Find the itinerary that visits the most destinations while respecting
    both budget and time as hard constraints.

    This is the function that should be used by BasicPlannerService for R2,
    because the project states that budget and time are hard constraints.

    Args:
        graph: Flight network graph.
        origen: Origin airport IATA code.
        presupuesto: Maximum available budget in USD.
        tiempo_disponible_min: Maximum available time in minutes.
        criterio_desempate: 'cost' or 'time'.
            - 'cost': if destination count is tied, choose lower total cost.
            - 'time': if destination count is tied, choose lower total time.
        incluir_secundarios: When False, secondary airports are excluded.
        tipos_transporte: Optional list of allowed aircraft types.
        aircraft_registry: Optional aircraft registry with JSON override rates.

    Returns:
        Standard result dictionary.
    """
    return _max_destinations_with_limits(
        graph=graph,
        origen=origen,
        budget_limit=presupuesto,
        time_limit=tiempo_disponible_min,
        tie_breaker=criterio_desempate,
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
        include_secondary=incluir_secundarios,
    )
"""
Shared utilities for the algorithms package.

Responsibility
--------------
This module contains reusable helpers used by path-finding algorithms such as
Dijkstra and constrained backtracking.

The goal is to keep each algorithm focused only on its search strategy, while
this module handles common concerns such as:

    - Aircraft registry construction.
    - Route filtering.
    - Cost, time and distance calculations.
    - Aircraft selection according to an optimization criterion.
    - Standard result formatting.

No external graph libraries are used.
"""

from __future__ import annotations

from typing import Any

from domain.models.aircraft import Aircraft, DEFAULT_AIRCRAFT
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph


DISTANCE_CRITERIA = {"distancia", "distance", "km"}
TIME_CRITERIA = {"tiempo", "time", "minutes", "min"}
COST_CRITERIA = {"costo", "cost", "usd", "price"}


def normalize_criterion(criterion: str) -> str:
    """
    Normalize an optimization criterion to one of: distance, time, cost.

    Args:
        criterion: Raw criterion string.

    Returns:
        Normalized criterion.

    Raises:
        ValueError: If the criterion is not supported.
    """
    value = criterion.strip().lower()

    if value in DISTANCE_CRITERIA:
        return "distance"

    if value in TIME_CRITERIA:
        return "time"

    if value in COST_CRITERIA:
        return "cost"

    raise ValueError(
        f"Unsupported optimization criterion '{criterion}'. "
        "Valid criteria are: distance, time, cost."
    )


def build_aircraft_registry(
    tipos_transporte: list[str] | None = None,
    aircraft_config: dict[str, dict[str, float]] | None = None,
) -> dict[str, Aircraft]:
    """
    Build and return an Aircraft registry.

    When tipos_transporte is None, all available aircraft types are included.

    The optional aircraft_config parameter allows JSON global configuration
    values to override DEFAULT_AIRCRAFT rates.

    Supported config key formats:
        - costo_km / tiempo_km
        - costoKm / tiempoKm

    Args:
        tipos_transporte: Allowed aircraft type names. None means all types.
        aircraft_config: Optional aircraft rates loaded from JSON config.

    Returns:
        Dict mapping aircraft name to Aircraft instance.
    """
    raw_config = dict(DEFAULT_AIRCRAFT)

    if aircraft_config:
        for name, values in aircraft_config.items():
            costo_km = values.get("costo_km", values.get("costoKm"))
            tiempo_km = values.get("tiempo_km", values.get("tiempoKm"))

            if costo_km is None or tiempo_km is None:
                continue

            raw_config[name] = {
                "costo_km": float(costo_km),
                "tiempo_km": float(tiempo_km),
            }

    names = tipos_transporte if tipos_transporte is not None else list(raw_config.keys())

    registry: dict[str, Aircraft] = {}

    for name in names:
        if name not in raw_config:
            continue

        data = raw_config[name]
        registry[name] = Aircraft(
            nombre=name,
            costo_km=float(data["costo_km"]),
            tiempo_km=float(data["tiempo_km"]),
        )

    return registry


def get_available_aircraft_for_route(
    route: Route,
    registry: dict[str, Aircraft],
) -> list[Aircraft]:
    """
    Return aircraft available for a route and allowed by the registry.

    Args:
        route: Route being evaluated.
        registry: Allowed aircraft registry.

    Returns:
        List of Aircraft objects that can operate the route.
    """
    return [
        registry[name]
        for name in route.aeronaves
        if name in registry
    ]


def calculate_route_cost(route: Route, aircraft: Aircraft) -> float:
    """
    Calculate the flight cost for a route and aircraft.

    Subsidised routes have zero cost. In this project, a route is considered
    subsidised when route.costo_base == 0.

    Args:
        route: Route being evaluated.
        aircraft: Aircraft selected for the route.

    Returns:
        Cost in USD.
    """
    if route.es_subsidiada:
        return 0.0

    return aircraft.calcular_costo(route.distancia_km)


def calculate_route_time(route: Route, aircraft: Aircraft) -> float:
    """
    Calculate the flight time for a route and aircraft.

    Args:
        route: Route being evaluated.
        aircraft: Aircraft selected for the route.

    Returns:
        Flight time in minutes.
    """
    return aircraft.calcular_tiempo(route.distancia_km)


def get_route_weight(
    route: Route,
    aircraft: Aircraft,
    criterion: str,
) -> float:
    """
    Return the route weight according to the optimization criterion.

    Args:
        route: Route being evaluated.
        aircraft: Aircraft selected for the route.
        criterion: distance, time or cost.

    Returns:
        Numeric weight used by path-finding algorithms.
    """
    normalized = normalize_criterion(criterion)

    if normalized == "distance":
        return float(route.distancia_km)

    if normalized == "time":
        return calculate_route_time(route, aircraft)

    if normalized == "cost":
        return calculate_route_cost(route, aircraft)

    raise ValueError(f"Unsupported criterion '{criterion}'.")


def select_best_aircraft(
    route: Route,
    registry: dict[str, Aircraft],
    criterion: str,
) -> Aircraft | None:
    """
    Select the best aircraft for a route according to a criterion.

    Selection rules:
        - distance: choose the fastest valid aircraft, because distance does
          not depend on aircraft.
        - time: choose the aircraft with the lowest flight time.
        - cost: choose the aircraft with the lowest cost. If there is a tie,
          choose the fastest one.

    Args:
        route: Route being evaluated.
        registry: Allowed aircraft registry.
        criterion: distance, time or cost.

    Returns:
        Best Aircraft object, or None if no valid aircraft is available.
    """
    available_aircraft = get_available_aircraft_for_route(route, registry)

    if not available_aircraft:
        return None

    normalized = normalize_criterion(criterion)

    if normalized == "distance":
        return min(
            available_aircraft,
            key=lambda aircraft: calculate_route_time(route, aircraft),
        )

    if normalized == "time":
        return min(
            available_aircraft,
            key=lambda aircraft: calculate_route_time(route, aircraft),
        )

    if normalized == "cost":
        return min(
            available_aircraft,
            key=lambda aircraft: (
                calculate_route_cost(route, aircraft),
                calculate_route_time(route, aircraft),
            ),
        )

    raise ValueError(f"Unsupported criterion '{criterion}'.")


def filter_valid_routes(
    graph: AdjacencyGraph,
    airport_id: str,
    registry: dict[str, Aircraft],
    include_secondary: bool,
) -> list[Route]:
    """
    Return outgoing, non-blocked routes that pass transport and hub filters.

    A route is included only when:
        - It is not blocked.
        - At least one of its aircraft types exists in the registry.
        - The destination is a hub when include_secondary is False.

    Args:
        graph: The flight network graph.
        airport_id: IATA code of the departure airport.
        registry: Allowed aircraft registry.
        include_secondary: When False, only hub destinations are returned.

    Returns:
        List of valid Route objects.
    """
    valid_routes: list[Route] = []

    for route in graph.get_neighbors(airport_id):
        if not get_available_aircraft_for_route(route, registry):
            continue

        if not include_secondary and not graph.get_node(route.destino).es_hub:
            continue

        valid_routes.append(route)

    return valid_routes


def build_leg(
    route: Route,
    aircraft: Aircraft,
) -> dict[str, Any]:
    """
    Build a standard dictionary representation for a flight leg.

    Args:
        route: Route included in the itinerary.
        aircraft: Aircraft selected for the route.

    Returns:
        Dictionary with leg details.
    """
    return {
        "origen": route.origen,
        "destino": route.destino,
        "aeronave": aircraft.nombre,
        "distancia_km": round(route.distancia_km, 2),
        "costo_usd": round(calculate_route_cost(route, aircraft), 2),
        "tiempo_min": round(calculate_route_time(route, aircraft), 2),
        "estancia_minima_min": route.estancia_minima,
        "subsidiada": route.es_subsidiada,
    }


def build_result(path: list[str], tramos: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Assemble the standard algorithm result dictionary.

    Args:
        path: Ordered list of IATA codes, origin first.
        tramos: Per-leg dictionaries generated by build_leg.

    Returns:
        Dictionary with route, legs and accumulated totals.
    """
    return {
        "ruta": list(path),
        "tramos": list(tramos),
        "cantidad_destinos": max(len(path) - 1, 0),
        "total_distancia_km": round(
            sum(t["distancia_km"] for t in tramos),
            2,
        ),
        "total_costo_usd": round(
            sum(t["costo_usd"] for t in tramos),
            2,
        ),
        "total_tiempo_min": round(
            sum(t["tiempo_min"] for t in tramos),
            2,
        ),
    }


def empty_result() -> dict[str, Any]:
    """
    Return a standard empty result.

    Useful when no route can be found.
    """
    return build_result(path=[], tramos=[])
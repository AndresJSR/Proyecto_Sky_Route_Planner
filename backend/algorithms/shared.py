"""
Shared utilities for the algorithms package (SOLID — S).

Responsibility
--------------
This module owns three infrastructure concerns shared by dijkstra.py and
backtracking.py.  Centralising them here satisfies SRP: each algorithm file
is responsible only for its algorithm logic, not for registry construction,
route filtering or result formatting.

    build_aircraft_registry  — builds an Aircraft dict from allowed types.
    filter_valid_routes      — returns traversable routes from an airport.
    build_result             — assembles the standard result dictionary.

These utilities have no knowledge of any specific algorithm; they are
intentionally algorithm-agnostic.
"""

from __future__ import annotations

from domain.models.aircraft import Aircraft, DEFAULT_AIRCRAFT
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph


def build_aircraft_registry(
    tipos_transporte: list[str] | None = None,
) -> dict[str, Aircraft]:
    """
    Build and return an Aircraft registry.

    When tipos_transporte is None all default aircraft types are included.
    Unknown type names are silently ignored.

    Args:
        tipos_transporte: Allowed aircraft type names; None means all types.

    Returns:
        Dict mapping aircraft name → Aircraft instance.
    """
    names = tipos_transporte if tipos_transporte is not None else list(DEFAULT_AIRCRAFT.keys())
    return {
        name: Aircraft.from_defaults(name)
        for name in names
        if name in DEFAULT_AIRCRAFT
    }


def filter_valid_routes(
    graph: AdjacencyGraph,
    airport_id: str,
    registry: dict[str, Aircraft],
    include_secondary: bool,
) -> list[Route]:
    """
    Return outgoing, non-blocked routes that pass transport and hub filters.

    A route is included only when:
      - At least one of its aircraft types exists in the registry.
      - The destination is a hub when include_secondary is False.

    Args:
        graph:             The flight network graph.
        airport_id:        IATA code of the departure airport.
        registry:          Allowed aircraft registry.
        include_secondary: When False, only hub destinations are returned.

    Returns:
        List of valid Route objects.
    """
    result = []
    for route in graph.get_neighbors(airport_id):
        if not any(name in registry for name in route.aeronaves):
            continue
        if not include_secondary and not graph.get_node(route.destino).es_hub:
            continue
        result.append(route)
    return result


def build_result(path: list[str], tramos: list[dict]) -> dict:
    """
    Assemble the standard algorithm result dictionary.

    Args:
        path:   Ordered list of IATA codes (origin first).
        tramos: Per-leg dicts with keys distancia_km, costo_usd, tiempo_min.

    Returns:
        Dict with ruta, tramos, and accumulated totals.
    """
    return {
        "ruta":               list(path),
        "tramos":             list(tramos),
        "total_distancia_km": round(sum(t["distancia_km"] for t in tramos), 2),
        "total_costo_usd":    round(sum(t["costo_usd"]    for t in tramos), 2),
        "total_tiempo_min":   round(sum(t["tiempo_min"]   for t in tramos), 2),
    }

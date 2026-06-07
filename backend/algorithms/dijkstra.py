"""
Dijkstra's shortest-path algorithm for the flight network.

Responsibility
--------------
This module implements Dijkstra's algorithm over the directed weighted
AdjacencyGraph.

It supports three optimization criteria:

    - cost
    - time
    - distance

The algorithm does not calculate route costs, times or aircraft selection
directly. Those shared concerns are delegated to algorithms.shared in order
to keep this file focused only on the shortest-path strategy.

Justification
-------------
The flight network is a directed weighted graph with non-negative edge
weights. Dijkstra's algorithm is appropriate because it guarantees the
minimum accumulated weight path when all edge weights are greater than or
equal to zero.

Complexity
----------
Using heapq as a min-priority queue:

    O((V + E) log V)

Where:
    V = number of airports
    E = number of routes
"""

from __future__ import annotations

import heapq
from itertools import count
from typing import Any

from algorithms.shared import (
    build_aircraft_registry,
    build_leg,
    build_result,
    filter_valid_routes,
    get_route_weight,
    normalize_criterion,
    select_best_aircraft,
)
from domain.models.aircraft import Aircraft
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph


PreviousStep = tuple[str, Route, Aircraft]
RequiredTransportState = tuple[str, frozenset[str]]
RequiredTransportPreviousStep = tuple[RequiredTransportState, Route, Aircraft]


def _resolve_registry(
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
) -> dict[str, Aircraft]:
    """
    Resolve the aircraft registry used by Dijkstra.

    Args:
        aircraft_registry: Optional existing registry, usually created from
                           JSON configuration.
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


def dijkstra(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    criterion: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
    include_secondary: bool = True,
) -> dict[str, Any] | None:
    """
    Find the shortest path between two airports using Dijkstra's algorithm.

    Args:
        graph: Flight network graph.
        origen: Origin airport IATA code.
        destino: Destination airport IATA code.
        criterion: Optimization criterion: cost, time or distance.
        aircraft_registry: Optional aircraft registry with operative rates.
        tipos_transporte: Optional list of allowed aircraft type names.
        include_secondary: When False, secondary airports are excluded from
                           route expansion.

    Returns:
        Standard result dictionary if a path exists, otherwise None.

    Raises:
        KeyError: If origin or destination airports do not exist.
        ValueError: If the optimization criterion is invalid.
    """
    normalized_criterion = normalize_criterion(criterion)

    if not graph.has_node(origen):
        raise KeyError(f"Origin airport '{origen}' not found in the graph.")

    if not graph.has_node(destino):
        raise KeyError(f"Destination airport '{destino}' not found in the graph.")

    registry = _resolve_registry(
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
    )

    if not registry:
        return None

    distances: dict[str, float] = {
        node.id: float("inf")
        for node in graph.get_all_nodes()
    }
    distances[origen] = 0.0

    previous: dict[str, PreviousStep | None] = {
        node.id: None
        for node in graph.get_all_nodes()
    }

    heap: list[tuple[float, str]] = [(0.0, origen)]
    visited: set[str] = set()

    while heap:
        current_distance, current_airport = heapq.heappop(heap)

        if current_airport in visited:
            continue

        visited.add(current_airport)

        if current_airport == destino:
            break

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
                criterion=normalized_criterion,
            )

            if aircraft is None:
                continue

            route_weight = get_route_weight(
                route=route,
                aircraft=aircraft,
                criterion=normalized_criterion,
            )

            candidate_distance = current_distance + route_weight

            if candidate_distance < distances[next_airport]:
                distances[next_airport] = candidate_distance
                previous[next_airport] = (current_airport, route, aircraft)
                heapq.heappush(heap, (candidate_distance, next_airport))

    if distances[destino] == float("inf"):
        return None

    path, legs = _reconstruct_path(
        origen=origen,
        destino=destino,
        previous=previous,
    )

    return build_result(path=path, tramos=legs)


def _reconstruct_path(
    origen: str,
    destino: str,
    previous: dict[str, PreviousStep | None],
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Reconstruct the final path after Dijkstra finishes.

    Args:
        origen: Origin airport IATA code.
        destino: Destination airport IATA code.
        previous: Previous-step dictionary generated by Dijkstra.

    Returns:
        Tuple containing:
            - Ordered airport path.
            - Ordered flight legs.
    """
    path: list[str] = []
    legs: list[dict[str, Any]] = []

    current = destino

    while current != origen:
        step = previous[current]

        if step is None:
            raise RuntimeError(
                f"Cannot reconstruct path from '{origen}' to '{destino}'."
            )

        parent, route, aircraft = step

        path.append(current)
        legs.append(build_leg(route=route, aircraft=aircraft))

        current = parent

    path.append(origen)
    path.reverse()
    legs.reverse()

    return path, legs


def dijkstra_con_transportes_requeridos(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    criterion: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
    include_secondary: bool = True,
    transportes_requeridos: list[str] | None = None,
) -> dict[str, Any] | None:
    """
    Find the shortest path requiring all selected transport types at least once.

    This is a Dijkstra variant with extended state:

        state = (current_airport, used_transport_types)

    A solution is valid only when:
        - current_airport == destino
        - used_transport_types contains every required transport type.

    This function does not replace the regular Dijkstra implementation. It is
    only used when the API explicitly asks to enforce the use of all selected
    transport types.

    Args:
        graph: Flight network graph.
        origen: Origin airport IATA code.
        destino: Destination airport IATA code.
        criterion: Optimization criterion: cost, time or distance.
        aircraft_registry: Optional aircraft registry with operative rates.
        tipos_transporte: Optional list of allowed aircraft type names.
        include_secondary: When False, secondary airports are excluded.
        transportes_requeridos: Transport types that must appear at least once
                                in the final route.

    Returns:
        Standard result dictionary if a valid path exists, otherwise None.
    """
    normalized_criterion = normalize_criterion(criterion)

    if not graph.has_node(origen):
        raise KeyError(f"Origin airport '{origen}' not found in the graph.")

    if not graph.has_node(destino):
        raise KeyError(f"Destination airport '{destino}' not found in the graph.")

    registry = _resolve_registry(
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
    )

    if not registry:
        return None

    required_transports = frozenset(
        transport
        for transport in (transportes_requeridos or tipos_transporte or [])
        if transport in registry
    )

    # If there are not at least two required transport types, the extra
    # constraint is not meaningful. Preserve the previous behavior.
    if len(required_transports) < 2:
        return dijkstra(
            graph=graph,
            origen=origen,
            destino=destino,
            criterion=normalized_criterion,
            aircraft_registry=registry,
            tipos_transporte=tipos_transporte,
            include_secondary=include_secondary,
        )

    start_state: RequiredTransportState = (origen, frozenset())

    distances: dict[RequiredTransportState, float] = {
        start_state: 0.0,
    }

    previous: dict[
        RequiredTransportState,
        RequiredTransportPreviousStep,
    ] = {}

    tie_breaker = count()

    heap: list[tuple[float, int, str, frozenset[str]]] = [
        (0.0, next(tie_breaker), origen, frozenset())
    ]

    final_state: RequiredTransportState | None = None

    while heap:
        current_distance, _, current_airport, used_transports = heapq.heappop(heap)
        current_state: RequiredTransportState = (current_airport, used_transports)

        if current_distance > distances.get(current_state, float("inf")):
            continue

        if (
            current_airport == destino
            and required_transports.issubset(used_transports)
        ):
            final_state = current_state
            break

        valid_routes = filter_valid_routes(
            graph=graph,
            airport_id=current_airport,
            registry=registry,
            include_secondary=include_secondary,
        )

        for route in valid_routes:
            next_airport = route.destino

            # Important:
            # The regular Dijkstra chooses only the best aircraft for a route.
            # Here we must evaluate every valid aircraft because a non-best
            # aircraft may be necessary to satisfy the transport requirement.
            for aircraft_name in route.aeronaves:
                aircraft = registry.get(aircraft_name)

                if aircraft is None:
                    continue

                next_used_transports = frozenset(
                    set(used_transports) | {aircraft.nombre}
                )

                next_state: RequiredTransportState = (
                    next_airport,
                    next_used_transports,
                )

                route_weight = get_route_weight(
                    route=route,
                    aircraft=aircraft,
                    criterion=normalized_criterion,
                )

                candidate_distance = current_distance + route_weight

                if candidate_distance < distances.get(next_state, float("inf")):
                    distances[next_state] = candidate_distance
                    previous[next_state] = (current_state, route, aircraft)

                    heapq.heappush(
                        heap,
                        (
                            candidate_distance,
                            next(tie_breaker),
                            next_airport,
                            next_used_transports,
                        ),
                    )

    if final_state is None:
        return None

    path, legs = _reconstruct_required_transport_path(
        origen=origen,
        final_state=final_state,
        start_state=start_state,
        previous=previous,
    )

    return build_result(path=path, tramos=legs)


def _reconstruct_required_transport_path(
    origen: str,
    final_state: RequiredTransportState,
    start_state: RequiredTransportState,
    previous: dict[RequiredTransportState, RequiredTransportPreviousStep],
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Reconstruct a path generated by dijkstra_con_transportes_requeridos.

    Args:
        origen: Origin airport IATA code.
        final_state: Accepted final state.
        start_state: Initial state.
        previous: Previous-step dictionary generated by the extended Dijkstra.

    Returns:
        Tuple containing:
            - Ordered airport path.
            - Ordered flight legs.
    """
    path: list[str] = []
    legs: list[dict[str, Any]] = []

    current_state = final_state

    while current_state != start_state:
        step = previous.get(current_state)

        if step is None:
            raise RuntimeError(
                f"Cannot reconstruct constrained path from '{origen}'."
            )

        previous_state, route, aircraft = step

        path.append(current_state[0])
        legs.append(build_leg(route=route, aircraft=aircraft))

        current_state = previous_state

    path.append(origen)
    path.reverse()
    legs.reverse()

    return path, legs


def dijkstra_costo(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
    include_secondary: bool = True,
) -> dict[str, Any] | None:
    """
    Find the route with the lowest total flight cost.

    Subsidised routes contribute 0 USD to the accumulated cost.
    """
    return dijkstra(
        graph=graph,
        origen=origen,
        destino=destino,
        criterion="cost",
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
        include_secondary=include_secondary,
    )


def dijkstra_tiempo(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
    include_secondary: bool = True,
) -> dict[str, Any] | None:
    """
    Find the route with the lowest total flight time.
    """
    return dijkstra(
        graph=graph,
        origen=origen,
        destino=destino,
        criterion="time",
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
        include_secondary=include_secondary,
    )


def dijkstra_distancia(
    graph: AdjacencyGraph,
    origen: str,
    destino: str,
    aircraft_registry: dict[str, Aircraft] | None = None,
    tipos_transporte: list[str] | None = None,
    include_secondary: bool = True,
) -> dict[str, Any] | None:
    """
    Find the route with the lowest total distance.
    """
    return dijkstra(
        graph=graph,
        origen=origen,
        destino=destino,
        criterion="distance",
        aircraft_registry=aircraft_registry,
        tipos_transporte=tipos_transporte,
        include_secondary=include_secondary,
    )
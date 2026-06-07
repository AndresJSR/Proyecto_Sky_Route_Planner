"""
Basic planner service.

Responsibility
--------------
This service exposes the basic itinerary planning use cases required by R2:

1. Calculate the best route between an origin and a destination according to:
   - distance
   - time
   - cost

2. Propose two itinerary alternatives:
   - Maximum number of destinations within both budget and available time,
     prioritizing lower cost as tie-breaker.
   - Maximum number of destinations within both budget and available time,
     prioritizing lower time as tie-breaker.

This service does not implement graph algorithms directly. It delegates that
work to the algorithms package.
"""

from __future__ import annotations

from typing import Any

from algorithms.backtracking import max_destinos_presupuesto_y_tiempo
from algorithms.dijkstra import dijkstra, dijkstra_con_transportes_requeridos
from algorithms.shared import build_aircraft_registry, normalize_criterion
from graph.adjacency_graph import AdjacencyGraph


class BasicPlannerService:
    """
    Proposes itineraries using Dijkstra and DFS/backtracking algorithms.

    This class is part of the application/service layer. It coordinates
    algorithms and input validation, but it does not know anything about
    frontend components or API controllers.
    """

    def __init__(self, graph: AdjacencyGraph, config: dict | None = None) -> None:
        self.graph = graph
        self.config = config or {}

    def calcular_ruta_optima(
        self,
        origen: str,
        destino: str,
        criterio: str,
        incluir_secundarios: bool = True,
        tipos_transporte: list[str] | None = None,
        exigir_todos_los_transportes: bool = False,
    ) -> dict[str, Any] | None:
        """
        Calculate the best route between two airports by the given criterion.

        Args:
            origen: Origin airport IATA code.
            destino: Destination airport IATA code.
            criterio: Optimization criterion: costo, tiempo or distancia.
            incluir_secundarios: When False, secondary airports are excluded.
            tipos_transporte: Allowed aircraft type names. None means all types.
            exigir_todos_los_transportes: When True, the route must use every
                selected aircraft type at least once. This only applies when
                tipos_transporte contains two or more transport types.

        Returns:
            Standard route result dictionary, or None if no path exists.
        """
        origen = origen.upper()
        destino = destino.upper()

        # Compatibility rule:
        # If the new requirement is enabled but tipos_transporte comes as [],
        # it must not fail. In that case, it behaves like the normal route
        # calculation with all transports available.
        if exigir_todos_los_transportes and tipos_transporte == []:
            tipos_transporte = None

        self._validate_airports(origen=origen, destino=destino)
        self._validate_transport_types(tipos_transporte)

        normalized_criterion = normalize_criterion(criterio)
        aircraft_registry = self._build_registry(tipos_transporte)

        should_require_all_transports = (
            exigir_todos_los_transportes is True
            and tipos_transporte is not None
            and len(tipos_transporte) >= 2
        )

        if should_require_all_transports:
            return dijkstra_con_transportes_requeridos(
                graph=self.graph,
                origen=origen,
                destino=destino,
                criterion=normalized_criterion,
                aircraft_registry=aircraft_registry,
                tipos_transporte=tipos_transporte,
                include_secondary=incluir_secundarios,
                transportes_requeridos=tipos_transporte,
            )

        return dijkstra(
            graph=self.graph,
            origen=origen,
            destino=destino,
            criterion=normalized_criterion,
            aircraft_registry=aircraft_registry,
            tipos_transporte=tipos_transporte,
            include_secondary=incluir_secundarios,
        )

    def proponer_itinerarios(
        self,
        origen: str,
        presupuesto: float,
        tiempo_disponible_horas: float,
        incluir_secundarios: bool = True,
        tipos_transporte: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Propose two basic itinerary alternatives.

        Both alternatives respect budget and time as hard constraints.

        Alternative A:
            Route that visits the maximum number of destinations without
            exceeding budget or time. If there is a tie, it chooses the
            itinerary with the lowest cost.

        Alternative B:
            Route that visits the maximum number of destinations without
            exceeding budget or time. If there is a tie, it chooses the
            itinerary with the lowest time.

        Args:
            origen: Origin airport IATA code.
            presupuesto: Available budget in USD.
            tiempo_disponible_horas: Available time in hours.
            incluir_secundarios: When False, secondary airports are excluded.
            tipos_transporte: Allowed aircraft type names. None means all types.

        Returns:
            Dictionary containing both proposed itinerary alternatives.
        """
        origen = origen.upper()

        self._validate_origin(origen)
        self._validate_positive_number(presupuesto, "presupuesto")
        self._validate_positive_number(
            tiempo_disponible_horas,
            "tiempo_disponible_horas",
        )
        self._validate_transport_types(tipos_transporte)

        tiempo_disponible_min = tiempo_disponible_horas * 60
        aircraft_registry = self._build_registry(tipos_transporte)

        alternativa_presupuesto = max_destinos_presupuesto_y_tiempo(
            graph=self.graph,
            origen=origen,
            presupuesto=presupuesto,
            tiempo_disponible_min=tiempo_disponible_min,
            criterio_desempate="cost",
            incluir_secundarios=incluir_secundarios,
            tipos_transporte=tipos_transporte,
            aircraft_registry=aircraft_registry,
            require_all_transport_types=True,
        )

        alternativa_tiempo = max_destinos_presupuesto_y_tiempo(
            graph=self.graph,
            origen=origen,
            presupuesto=presupuesto,
            tiempo_disponible_min=tiempo_disponible_min,
            criterio_desempate="time",
            incluir_secundarios=incluir_secundarios,
            tipos_transporte=tipos_transporte,
            aircraft_registry=aircraft_registry,
            require_all_transport_types=True,
        )

        return {
            "origen": origen,
            "restricciones": {
                "presupuesto_usd": presupuesto,
                "tiempo_disponible_horas": tiempo_disponible_horas,
                "tiempo_disponible_min": tiempo_disponible_min,
                "incluir_secundarios": incluir_secundarios,
                "tipos_transporte": tipos_transporte or "todos",
            },
            "alternativas": {
                "mayor_cantidad_destinos_por_presupuesto": alternativa_presupuesto,
                "mayor_cantidad_destinos_por_tiempo": alternativa_tiempo,
            },
        }

    def calcular_rutas_por_criterios(
        self,
        origen: str,
        destino: str,
        criterios: list[str],
        incluir_secundarios: bool = True,
        tipos_transporte: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate one optimal route for each selected optimization criterion.

        This supports the project requirement where the user can select one
        or multiple criteria.

        Args:
            origen: Origin airport IATA code.
            destino: Destination airport IATA code.
            criterios: List of criteria: costo, tiempo, distancia.
            incluir_secundarios: When False, secondary airports are excluded.
            tipos_transporte: Allowed aircraft type names. None means all types.

        Returns:
            Dictionary mapping each normalized criterion to its route result.
        """
        origen = origen.upper()
        destino = destino.upper()

        if not criterios:
            raise ValueError("At least one optimization criterion must be provided.")

        resultados: dict[str, Any] = {}

        for criterio in criterios:
            normalized = normalize_criterion(criterio)
            resultados[normalized] = self.calcular_ruta_optima(
                origen=origen,
                destino=destino,
                criterio=normalized,
                incluir_secundarios=incluir_secundarios,
                tipos_transporte=tipos_transporte,
            )

        return {
            "origen": origen,
            "destino": destino,
            "criterios": [normalize_criterion(c) for c in criterios],
            "resultados": resultados,
        }

    def _build_registry(
        self,
        tipos_transporte: list[str] | None = None,
    ):
        """
        Build the aircraft registry using JSON config overrides if available.
        """
        aircraft_config = self.config.get("aeronaves")

        return build_aircraft_registry(
            tipos_transporte=tipos_transporte,
            aircraft_config=aircraft_config,
        )

    def _validate_origin(self, origen: str) -> None:
        """
        Validate that the origin airport exists in the graph.
        """
        if not self.graph.has_node(origen):
            raise KeyError(f"Origin airport '{origen}' not found in the graph.")

    def _validate_airports(self, origen: str, destino: str) -> None:
        """
        Validate that both origin and destination airports exist in the graph.
        """
        self._validate_origin(origen)

        if not self.graph.has_node(destino):
            raise KeyError(f"Destination airport '{destino}' not found in the graph.")

    def _validate_transport_types(
        self,
        tipos_transporte: list[str] | None,
    ) -> None:
        """
        Validate selected aircraft types.

        None means all aircraft types are allowed.
        An empty list is invalid because the user must select at least one type
        when they provide a custom selection.
        """
        if tipos_transporte is not None and len(tipos_transporte) == 0:
            raise ValueError("At least one transport type must be selected.")

    def _validate_positive_number(self, value: float, field_name: str) -> None:
        """
        Validate that a numeric field is greater than or equal to zero.
        """
        if value < 0:
            raise ValueError(f"'{field_name}' cannot be negative.")
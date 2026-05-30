"""
Graph controller.

Responsibility
--------------
This controller exposes graph query operations to an external interface,
such as a future REST API, CLI adapter, or frontend layer.

It does not access the AdjacencyGraph directly. It delegates all graph
queries to GraphService.

This file is intentionally framework-independent so it can later be connected
to FastAPI, Flask, or any frontend adapter without changing the service layer.
"""

from __future__ import annotations

from typing import Any

from services.graph_service import GraphService


class GraphController:
    """
    Controller for graph query operations.

    Public methods:
        - get_network_summary
        - get_airports
        - get_airport_detail
        - get_routes
        - get_neighbors
        - get_blocked_routes
        - airport_exists
        - route_exists

    All methods receive a dictionary payload when input is needed and return
    a standardized response dictionary.
    """

    def __init__(self, graph_service: GraphService) -> None:
        self.graph_service = graph_service

    def get_network_summary(self) -> dict[str, Any]:
        """
        Return general statistics about the loaded flight network.
        """
        try:
            result = self.graph_service.obtener_resumen_red()
            return self._success(data=result)
        except Exception as exc:
            return self._error(exc)

    def get_airports(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Return all airports, optionally filtered to hubs only.

        Expected payload:
            {
                "solo_hubs": false
            }
        """
        try:
            payload = payload or {}
            solo_hubs = bool(payload.get("solo_hubs", False))

            result = self.graph_service.listar_aeropuertos(
                solo_hubs=solo_hubs,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def get_airport_detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Return full information for a specific airport.

        Expected payload:
            {
                "airport_id": "BOG"
            }
        """
        try:
            airport_id = self._require_str(payload, "airport_id")

            result = self.graph_service.obtener_info_aeropuerto(
                airport_id=airport_id,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def get_routes(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Return all routes, optionally including blocked routes.

        Expected payload:
            {
                "include_blocked": true
            }
        """
        try:
            payload = payload or {}
            include_blocked = bool(payload.get("include_blocked", False))

            result = self.graph_service.listar_rutas(
                include_blocked=include_blocked,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def get_neighbors(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Return outgoing routes from a specific airport.

        Expected payload:
            {
                "airport_id": "BOG",
                "include_blocked": false
            }
        """
        try:
            airport_id = self._require_str(payload, "airport_id")
            include_blocked = bool(payload.get("include_blocked", False))

            result = self.graph_service.obtener_rutas_desde(
                airport_id=airport_id,
                include_blocked=include_blocked,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def get_blocked_routes(self) -> dict[str, Any]:
        """
        Return all currently blocked routes.
        """
        try:
            result = self.graph_service.listar_rutas_bloqueadas()
            return self._success(data=result)
        except Exception as exc:
            return self._error(exc)

    def airport_exists(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Check whether an airport exists in the graph.

        Expected payload:
            {
                "airport_id": "BOG"
            }
        """
        try:
            airport_id = self._require_str(payload, "airport_id")

            result = {
                "airport_id": airport_id,
                "exists": self.graph_service.existe_aeropuerto(airport_id),
            }

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def route_exists(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Check whether a direct route exists between origin and destination.

        Expected payload:
            {
                "origen": "BOG",
                "destino": "SCL"
            }
        """
        try:
            origen = self._require_str(payload, "origen")
            destino = self._require_str(payload, "destino")

            result = {
                "origen": origen,
                "destino": destino,
                "exists": self.graph_service.existe_ruta(
                    origen=origen,
                    destino=destino,
                ),
            }

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _success(self, data: Any) -> dict[str, Any]:
        """
        Build a successful controller response.
        """
        return {
            "ok": True,
            "data": data,
            "error": None,
        }

    def _error(self, exc: Exception) -> dict[str, Any]:
        """
        Build an error controller response.
        """
        return {
            "ok": False,
            "data": None,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }

    # ------------------------------------------------------------------
    # Payload validators
    # ------------------------------------------------------------------

    def _require_str(self, payload: dict[str, Any], field: str) -> str:
        """
        Extract and validate a required string field.
        """
        value = payload.get(field)

        if value is None:
            raise ValueError(f"Missing required field: '{field}'.")

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{field}' must be a non-empty string.")

        return value.strip().upper()
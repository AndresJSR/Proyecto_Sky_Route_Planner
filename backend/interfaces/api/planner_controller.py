"""
Planner controller.

Responsibility
--------------
This controller exposes the basic planning use cases to an external interface,
such as a future REST API or frontend layer.

It does not implement algorithms directly. It delegates all planning logic to
BasicPlannerService.

This file is intentionally framework-independent so it can later be connected
to FastAPI, Flask, a CLI, or any frontend adapter without changing the
application logic.
"""

from __future__ import annotations

from typing import Any

from services.basic_planner_service import BasicPlannerService


class PlannerController:
    """
    Controller for basic route planning operations.

    Public methods:
        - calculate_optimal_route
        - calculate_routes_by_criteria
        - propose_itineraries

    All methods receive a dictionary payload and return a standardized
    response dictionary.
    """

    def __init__(self, planner_service: BasicPlannerService) -> None:
        self.planner_service = planner_service

    def calculate_optimal_route(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate the best route between origin and destination.

        Expected payload:
            {
                "origen": "BOG",
                "destino": "SCL",
                "criterio": "costo",
                "incluir_secundarios": true,
                "tipos_transporte": ["Avión Comercial", "Hélice"],
                "exigir_todos_los_transportes": true
            }

        The field "exigir_todos_los_transportes" is optional. When it is not
        provided or is false, the behavior remains the same as before.
        """
        try:
            origen = self._require_str(payload, "origen")
            destino = self._require_str(payload, "destino")
            criterio = self._require_str(payload, "criterio")

            incluir_secundarios = payload.get("incluir_secundarios", True)
            tipos_transporte = payload.get("tipos_transporte")
            exigir_todos_los_transportes = self._optional_bool(
                payload=payload,
                field="exigir_todos_los_transportes",
                default=False,
            )

            result = self.planner_service.calcular_ruta_optima(
                origen=origen,
                destino=destino,
                criterio=criterio,
                incluir_secundarios=bool(incluir_secundarios),
                tipos_transporte=tipos_transporte,
                exigir_todos_los_transportes=exigir_todos_los_transportes,
            )

            if self._should_return_transport_constraint_not_found(
                result=result,
                exigir_todos_los_transportes=exigir_todos_los_transportes,
                tipos_transporte=tipos_transporte,
            ):
                return self._transport_constraint_not_found()

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def calculate_routes_by_criteria(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate one optimal route for each selected criterion.

        Expected payload:
            {
                "origen": "BOG",
                "destino": "SCL",
                "criterios": ["costo", "tiempo", "distancia"],
                "incluir_secundarios": true,
                "tipos_transporte": null
            }
        """
        try:
            origen = self._require_str(payload, "origen")
            destino = self._require_str(payload, "destino")
            criterios = self._require_list(payload, "criterios")

            incluir_secundarios = payload.get("incluir_secundarios", True)
            tipos_transporte = payload.get("tipos_transporte")

            result = self.planner_service.calcular_rutas_por_criterios(
                origen=origen,
                destino=destino,
                criterios=criterios,
                incluir_secundarios=bool(incluir_secundarios),
                tipos_transporte=tipos_transporte,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def propose_itineraries(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Propose two basic itineraries:
            1. Maximum destinations within budget.
            2. Maximum destinations within available time.

        Expected payload:
            {
                "origen": "BOG",
                "presupuesto": 700,
                "tiempo_disponible_horas": 72,
                "incluir_secundarios": true,
                "tipos_transporte": null
            }
        """
        try:
            origen = self._require_str(payload, "origen")
            presupuesto = self._require_number(payload, "presupuesto")
            tiempo_disponible_horas = self._require_number(
                payload,
                "tiempo_disponible_horas",
            )

            incluir_secundarios = payload.get("incluir_secundarios", True)
            tipos_transporte = payload.get("tipos_transporte")

            result = self.planner_service.proponer_itinerarios(
                origen=origen,
                presupuesto=presupuesto,
                tiempo_disponible_horas=tiempo_disponible_horas,
                incluir_secundarios=bool(incluir_secundarios),
                tipos_transporte=tipos_transporte,
            )

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

    def _transport_constraint_not_found(self) -> dict[str, Any]:
        """
        Build a controlled response when no route satisfies the transport
        constraint requested by the user.

        This is not an internal server error. The request was valid, but there
        is no feasible route that uses all selected transport types.
        """
        return {
            "ok": True,
            "data": None,
            "error": {
                "type": "NoRouteFound",
                "message": (
                    "No se encontró una ruta que cumpla la restricción "
                    "de usar todos los transportes seleccionados."
                ),
            },
        }

    def _should_return_transport_constraint_not_found(
        self,
        result: dict[str, Any] | None,
        exigir_todos_los_transportes: bool,
        tipos_transporte: Any,
    ) -> bool:
        """
        Decide if the controller should return the controlled no-route response
        for the transport constraint.

        The special response only applies when the user explicitly asked to use
        all selected transport types and provided at least two types.
        """
        return (
            result is None
            and exigir_todos_los_transportes is True
            and isinstance(tipos_transporte, list)
            and len(tipos_transporte) >= 2
        )

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

        return value.strip().upper() if field in {"origen", "destino"} else value.strip()

    def _require_number(self, payload: dict[str, Any], field: str) -> float:
        """
        Extract and validate a required numeric field.
        """
        value = payload.get(field)

        if value is None:
            raise ValueError(f"Missing required field: '{field}'.")

        if not isinstance(value, int | float):
            raise ValueError(f"Field '{field}' must be numeric.")

        return float(value)

    def _require_list(self, payload: dict[str, Any], field: str) -> list[str]:
        """
        Extract and validate a required list field.
        """
        value = payload.get(field)

        if value is None:
            raise ValueError(f"Missing required field: '{field}'.")

        if not isinstance(value, list):
            raise ValueError(f"Field '{field}' must be a list.")

        if len(value) == 0:
            raise ValueError(f"Field '{field}' cannot be empty.")

        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError(f"All values in '{field}' must be non-empty strings.")

        return [item.strip() for item in value]

    def _optional_bool(
        self,
        payload: dict[str, Any],
        field: str,
        default: bool = False,
    ) -> bool:
        """
        Extract and validate an optional boolean field.
        """
        value = payload.get(field, default)

        if not isinstance(value, bool):
            raise ValueError(f"Field '{field}' must be boolean.")

        return value
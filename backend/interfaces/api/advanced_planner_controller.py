"""
Advanced planner controller.

Responsibility
--------------
This controller exposes advanced step-by-step trip planning to the API layer.

It does not implement algorithms directly. It delegates all planning logic to
AdvancedPlannerService.

This file is intentionally framework-independent so it can later be connected
to FastAPI, Flask, a CLI, or any frontend adapter without changing the
application logic.
"""

from __future__ import annotations

from typing import Any

from services.advanced_planner_service import AdvancedPlannerService


class AdvancedPlannerController:
    """
    Controller for advanced step-by-step route planning operations.

    Public methods:
        - iniciar_viaje
        - avanzar_paso
        - realizar_actividad
        - tomar_trabajo

    All methods receive a dictionary payload and return a standardized
    response dictionary.
    """

    def __init__(self, planner_service: AdvancedPlannerService) -> None:
        self.planner_service = planner_service

    def iniciar_viaje(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Initialize a new traveler journey.

        Expected payload:
            {
                "origen": "BOG",
                "presupuesto_inicial": 1000,
                "tiempo_total_horas": 120
            }
        """
        try:
            origen = self._require_str(payload, "origen")
            presupuesto_inicial = self._require_number(
                payload,
                "presupuesto_inicial",
            )
            tiempo_total_horas = payload.get(
                "tiempo_total_horas",
                120,
            )

            result = self.planner_service.iniciar_viaje(
                origen=origen,
                presupuesto_inicial=presupuesto_inicial,
                tiempo_total_horas=tiempo_total_horas,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def avanzar_paso(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Perform a flight step in the journey.

        Expected payload:
            {
                "estado": {...},
                "destino": "SCL",
                "aeronave": "Avión Comercial"
            }
        """
        try:
            estado = self._require_dict(payload, "estado")
            destino = self._require_str(payload, "destino")
            aeronave = self._require_str(payload, "aeronave")

            result = self.planner_service.avanzar_paso(
                estado=estado,
                destino=destino,
                aeronave=aeronave,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def realizar_actividad(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Perform an activity at the current airport.

        Expected payload:
            {
                "estado": {...},
                "actividad_nombre": "Museo de Arte"
            }
        """
        try:
            estado = self._require_dict(payload, "estado")
            actividad_nombre = self._require_str(
                payload,
                "actividad_nombre",
            )

            result = self.planner_service.realizar_actividad(
                estado=estado,
                actividad_nombre=actividad_nombre,
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def tomar_trabajo(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Take a job at the current airport.

        Expected payload:
            {
                "estado": {...},
                "trabajo_nombre": "Consultor TI",
                "horas": 8
            }
        """
        try:
            estado = self._require_dict(payload, "estado")
            trabajo_nombre = self._require_str(
                payload,
                "trabajo_nombre",
            )
            horas = self._require_number(payload, "horas")

            result = self.planner_service.tomar_trabajo(
                estado=estado,
                trabajo_nombre=trabajo_nombre,
                horas=horas,
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

        return (
            value.strip().upper()
            if field in {"origen", "destino"}
            else value.strip()
        )

    def _require_number(self, payload: dict[str, Any], field: str) -> float:
        """
        Extract and validate a required numeric field.
        """
        value = payload.get(field)

        if value is None:
            raise ValueError(f"Missing required field: '{field}'.")

        if not isinstance(value, (int, float)):
            raise ValueError(f"Field '{field}' must be numeric.")

        return float(value)

    def _require_dict(self, payload: dict[str, Any], field: str) -> dict:
        """
        Extract and validate a required dictionary field.
        """
        value = payload.get(field)

        if value is None:
            raise ValueError(f"Missing required field: '{field}'.")

        if not isinstance(value, dict):
            raise ValueError(f"Field '{field}' must be a dictionary.")

        return value

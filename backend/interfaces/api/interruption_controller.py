"""
Interruption controller.

Responsibility
--------------
This controller exposes route interruption and itinerary recalculation
to the API layer.

It does not implement algorithms directly. It delegates all logic to
InterruptionService.

This file is intentionally framework-independent so it can later be connected
to FastAPI, Flask, a CLI, or any frontend adapter without changing the
application logic.
"""

from __future__ import annotations

from typing import Any

from services.interruption_service import InterruptionService


class InterruptionController:
    """
    Controller for handling route interruptions and recalculations.

    Public methods:
        - bloquear_ruta
        - desbloquear_ruta
        - recalcular_itinerario

    All methods receive a dictionary payload and return a standardized
    response dictionary.
    """

    def __init__(self, interruption_service: InterruptionService) -> None:
        self.interruption_service = interruption_service

    def bloquear_ruta(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Block a route between two airports.

        Expected payload:
            {
                "origen": "BOG",
                "destino": "SCL"
            }
        """
        try:
            origen = self._require_str(payload, "origen")
            destino = self._require_str(payload, "destino")

            self.interruption_service.bloquear_ruta(
                origen=origen,
                destino=destino,
            )

            return self._success(
                data={
                    "bloqueada": True,
                    "origen": origen,
                    "destino": destino,
                }
            )

        except Exception as exc:
            return self._error(exc)

    def desbloquear_ruta(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Unblock a route between two airports.

        Expected payload:
            {
                "origen": "BOG",
                "destino": "SCL"
            }
        """
        try:
            origen = self._require_str(payload, "origen")
            destino = self._require_str(payload, "destino")

            self.interruption_service.desbloquear_ruta(
                origen=origen,
                destino=destino,
            )

            return self._success(
                data={
                    "desbloqueada": True,
                    "origen": origen,
                    "destino": destino,
                }
            )

        except Exception as exc:
            return self._error(exc)

    def recalcular_itinerario(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Recalculate the itinerary after a route interruption.

        Expected payload:
            {
                "estado_viajero": {...},
                "destino_final": "SCL",
                "criterio": "distancia",
                "incluir_secundarios": true,
                "tipos_transporte": null
            }
        """
        try:
            estado_viajero = self._require_dict(
                payload,
                "estado_viajero",
            )
            destino_final = self._require_str(
                payload,
                "destino_final",
            )
            criterio = payload.get("criterio", "distancia")
            incluir_secundarios = payload.get(
                "incluir_secundarios",
                True,
            )
            tipos_transporte = payload.get("tipos_transporte")

            result = (
                self.interruption_service.recalcular_itinerario(
                    estado_viajero=estado_viajero,
                    destino_final=destino_final,
                    criterio=criterio,
                    incluir_secundarios=bool(incluir_secundarios),
                    tipos_transporte=tipos_transporte,
                )
            )

            return self._success(data=result)

        except Exception as exc:
            return self._error(exc)

    def manejar_interrupcion_en_transito(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle a mid-flight interruption (R4 in-transit state).

        If the traveler is in transit, refunds the flight and returns them
        to the origin airport.

        Expected payload:
            {
                "estado": {...}
            }
        """
        try:
            estado = self._require_dict(payload, "estado")

            result = (
                self.interruption_service
                .manejar_interrupcion_en_transito(estado)
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
            if field in {"origen", "destino", "destino_final"}
            else value.strip()
        )

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

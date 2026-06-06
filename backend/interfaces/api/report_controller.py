"""
Report controller.

Responsibility
--------------
This controller exposes trip reporting to the API layer.

It does not implement algorithms directly. It delegates all report generation
to ReportService.

This file is intentionally framework-independent so it can later be connected
to FastAPI, Flask, a CLI, or any frontend adapter without changing the
application logic.
"""

from __future__ import annotations

from typing import Any

from services.report_service import ReportService


class ReportController:
    """
    Controller for generating travel reports.

    Public methods:
        - generar_reporte

    All methods receive a dictionary payload and return a standardized
    response dictionary.
    """

    def __init__(self, report_service: ReportService) -> None:
        self.report_service = report_service

    def generar_reporte(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a complete travel report from final traveler state.

        Expected payload:
            {
                "estado_final": {...}
            }
        """
        try:
            estado_final = self._require_dict(payload, "estado_final")

            result = self.report_service.generar_reporte(
                estado_final=estado_final
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

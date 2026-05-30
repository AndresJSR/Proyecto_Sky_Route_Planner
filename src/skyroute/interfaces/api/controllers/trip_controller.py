"""Trip controller placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ....application.services import InterruptionService


@dataclass(slots=True)
class TripController:
    """Placeholder controller for trip interruption and lifecycle actions."""

    interruption_service: InterruptionService

    def block_route(self, origin_code: str, destination_code: str) -> None:
        """Block a route from the API layer."""
        self.interruption_service.block_route(origin_code, destination_code)

    def unblock_route(self, origin_code: str, destination_code: str) -> None:
        """Unblock a route from the API layer."""
        self.interruption_service.unblock_route(origin_code, destination_code)

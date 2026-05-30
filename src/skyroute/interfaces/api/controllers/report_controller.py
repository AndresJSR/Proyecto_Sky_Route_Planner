"""Report controller placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ....application.services import ReportService


@dataclass(slots=True)
class ReportController:
    """Placeholder controller for reports."""

    report_service: ReportService

    def get_network_summary(self) -> dict[str, int]:
        """Return a simple network summary."""
        return self.report_service.generate_network_summary()

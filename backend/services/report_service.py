# Stub for Persona 3 — Report service
# TODO: Implement final trip report generation
class ReportService:
    """Generates the final travel report from the completed traveler state."""

    def generar_reporte(self, estado_final: dict) -> dict:
        """
        Build the complete trip report including:
          - Visited destinations (name, city, country, stay time, cost)
          - Flown legs (origin, destination, aircraft, distance, time, cost)
          - Activities performed (name, type, time, cost)
          - Jobs performed (name, hours, income)
          - Totals (initial budget, spent, earned, balance, total time)
        """
        raise NotImplementedError

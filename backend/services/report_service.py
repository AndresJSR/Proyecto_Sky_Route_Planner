from __future__ import annotations

from graph.adjacency_graph import AdjacencyGraph


class ReportService:
    """
    Generates the final travel report from the completed traveler state.
    """

    def __init__(self, graph: AdjacencyGraph) -> None:
        self.graph = graph

    def generar_reporte(self, estado_final: dict) -> dict:
        """
        Build the complete trip report.
        """

        presupuesto_inicial = estado_final["presupuesto_inicial"]
        total_gastado = estado_final["gasto_total"]
        total_ganado = estado_final["ganancia_total"]
        saldo_final = estado_final["presupuesto_actual"]

        tiempo_total = (
            estado_final["tiempo_total_min"]
            - estado_final["tiempo_restante_min"]
        )

        return {
            "resumen": {
                "presupuesto_inicial": presupuesto_inicial,
                "total_gastado": round(total_gastado, 2),
                "total_ganado": round(total_ganado, 2),
                "saldo_final": round(saldo_final, 2),
                "tiempo_total_min": round(tiempo_total, 2),
                "tiempo_restante_min": round(
                    estado_final["tiempo_restante_min"], 2
                ),
            },

            "destinos_visitados": {
                "cantidad": len(estado_final["destinos_visitados"]),
                "destinos": list(estado_final["destinos_visitados"]),
                # R5: rich per-destination detail
                "detalle": self._build_detalle_destinos(estado_final),
            },

            "vuelos": {
                "cantidad": len(estado_final["vuelos"]),
                "detalle": list(estado_final["vuelos"]),
            },

            "actividades": {
                "cantidad": len(estado_final["actividades"]),
                "detalle": list(estado_final["actividades"]),
            },

            "trabajos": {
                "cantidad": len(estado_final["trabajos"]),
                "detalle": list(estado_final["trabajos"]),
            },
        }

    # ------------------------------------------------------------------
    # R5 helper
    # ------------------------------------------------------------------

    def _build_detalle_destinos(self, estado_final: dict) -> list[dict]:
        """
        Return a list of per-destination records in visit order.

        Each record contains:
            iata             : IATA code
            nombre           : Full airport name
            ciudad           : City
            pais             : Country
            costo_total_usd  : Sum of all costs incurred while at / departing
                               from this airport (flights, meals, lodging,
                               activities).
            tiempo_total_min : Total time spent at this airport.
        """
        ledger: dict = estado_final.get("detalle_por_destino", {})
        result = []
        for iata in estado_final["destinos_visitados"]:
            entry = ledger.get(iata, {"costo_total": 0.0, "tiempo_total_min": 0.0})
            try:
                airport = self.graph.get_node(iata)
                nombre = airport.nombre
                ciudad = airport.ciudad
                pais   = airport.pais
            except (KeyError, AttributeError):
                nombre = iata
                ciudad = ""
                pais   = ""
            result.append(
                {
                    "iata":             iata,
                    "nombre":           nombre,
                    "ciudad":           ciudad,
                    "pais":             pais,
                    "costo_total_usd":  round(entry["costo_total"], 2),
                    "tiempo_total_min": round(entry["tiempo_total_min"], 2),
                }
            )
        return result

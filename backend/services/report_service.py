from __future__ import annotations


class ReportService:
    """
    Generates the final travel report from the completed traveler state.
    """

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
                    estado_final["tiempo_restante_min"],
                    2,
                ),
            },

            "destinos_visitados": {
                "cantidad": len(
                    estado_final["destinos_visitados"]
                ),
                "destinos": list(
                    estado_final["destinos_visitados"]
                ),
            },

            "vuelos": {
                "cantidad": len(
                    estado_final["vuelos"]
                ),
                "detalle": list(
                    estado_final["vuelos"]
                ),
            },

            "actividades": {
                "cantidad": len(
                    estado_final["actividades"]
                ),
                "detalle": list(
                    estado_final["actividades"]
                ),
            },

            "trabajos": {
                "cantidad": len(
                    estado_final["trabajos"]
                ),
                "detalle": list(
                    estado_final["trabajos"]
                ),
            },
        }
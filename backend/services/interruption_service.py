from __future__ import annotations

from graph.adjacency_graph import AdjacencyGraph
from services.basic_planner_service import BasicPlannerService


class InterruptionService:
    """
    Handles real-time route interruptions and itinerary recalculation.
    """

    def __init__(
        self,
        graph: AdjacencyGraph,
        planner: BasicPlannerService,
    ) -> None:

        self.graph = graph
        self.planner = planner

    # BLOQUEAR

    def bloquear_ruta(
        self,
        origen: str,
        destino: str,
    ) -> None:

        self.graph.block_route(
            origen.upper(),
            destino.upper(),
        )

    # DESBLOQUEAR

    def desbloquear_ruta(
        self,
        origen: str,
        destino: str,
    ) -> None:

        self.graph.unblock_route(
            origen.upper(),
            destino.upper(),
        )

    # CONSULTAR

    def listar_rutas_bloqueadas(self) -> list[dict]:

        rutas = self.graph.get_blocked_routes()

        return [
            {
                "origen": r.origen,
                "destino": r.destino,
                "distancia_km": r.distancia_km,
            }
            for r in rutas
        ]

    # RECALCULAR

    def recalcular_itinerario(
        self,
        estado_viajero: dict,
        destino_final: str,
        criterio: str = "distancia",
        incluir_secundarios: bool = True,
        tipos_transporte: list[str] | None = None,
    ) -> dict:
        """
        Recalculate the optimal route from the traveler's
        current airport after an interruption.
        """

        origen_actual = estado_viajero["aeropuerto_actual"]

        nueva_ruta = self.planner.calcular_ruta_optima(
            origen=origen_actual,
            destino=destino_final,
            criterio=criterio,
            incluir_secundarios=incluir_secundarios,
            tipos_transporte=tipos_transporte,
        )

        if nueva_ruta is None:
            return {
                "recalculado": False,
                "mensaje": (
                    f"No available route from "
                    f"{origen_actual} to {destino_final}"
                ),
            }

        return {
            "recalculado": True,
            "origen_actual": origen_actual,
            "destino_final": destino_final,
            "nuevo_itinerario": nueva_ruta,
        }

    # VALIDACIÓN

    def ruta_esta_bloqueada(
        self,
        origen: str,
        destino: str,
    ) -> bool:

        route = self.graph.get_route(
            origen.upper(),
            destino.upper(),
        )

        if route is None:
            return False

        return route.bloqueada

    # R4: IN-TRANSIT INTERRUPTION

    def manejar_interrupcion_en_transito(
        self,
        estado: dict,
    ) -> dict:
        """
        Handle a mid-flight interruption.

        If the traveler is currently in transit (en_transito=True), refund
        the flight cost and time, undo distance tracking, and return the
        traveler to the origin airport.  The minimum-stay time already
        consumed as free time is intentionally kept (the stay occurred).

        Returns a dict describing the outcome.
        """
        if not estado.get("en_transito"):
            return {
                "redirigido": False,
                "mensaje": "Traveler is not currently in transit.",
            }

        vuelo = estado["vuelo_en_curso"]
        origen = vuelo["origen"]

        # Refund flight cost
        estado["presupuesto_actual"] += vuelo["costo"]
        estado["gasto_total"] -= vuelo["costo"]

        # Refund flight time and meal/lodge counters
        estado["tiempo_restante_min"] += vuelo["tiempo_min"]
        estado["minutos_desde_comida"] = max(
            0, estado["minutos_desde_comida"] - vuelo["tiempo_min"]
        )
        estado["minutos_desde_alojamiento"] = max(
            0, estado["minutos_desde_alojamiento"] - vuelo["tiempo_min"]
        )

        # Undo distance accumulation
        estado["distancia_total"] -= vuelo["distancia_km"]
        if vuelo["subsidiada"]:
            estado["distancia_subsidiada"] -= vuelo["distancia_km"]

        # Return traveler to origin
        estado["aeropuerto_actual"] = origen

        # Clear transit state
        estado["en_transito"] = False
        estado["vuelo_en_curso"] = None

        return {
            "redirigido": True,
            "aeropuerto_retorno": origen,
            "mensaje": (
                f"Flight interrupted. Traveler returned to {origen}."
            ),
            "estado": estado,
        }
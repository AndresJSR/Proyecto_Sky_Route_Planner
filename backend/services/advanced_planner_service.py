from __future__ import annotations

from domain.models.aircraft import Aircraft
from graph.adjacency_graph import AdjacencyGraph


class AdvancedPlannerService:
    """
    Step-by-step traveler simulation with dynamic budget and activities.
    """

    COMIDA_CADA_MIN = 480      # 8 horas
    ALOJAMIENTO_CADA_MIN = 1200  # 20 horas

    def __init__(self, graph: AdjacencyGraph, config: dict) -> None:
        self.graph = graph
        self.config = config

    # INICIAR VIAJE

    def iniciar_viaje(
        self,
        origen: str,
        presupuesto_inicial: float,
        tiempo_total_horas: float = 120,
    ) -> dict:

        origen = origen.upper()

        if not self.graph.has_node(origen):
            raise KeyError(f"Airport '{origen}' not found.")

        return {
            "aeropuerto_actual": origen,

            "presupuesto_inicial": presupuesto_inicial,
            "presupuesto_actual": presupuesto_inicial,

            "tiempo_total_min": tiempo_total_horas * 60,
            "tiempo_restante_min": tiempo_total_horas * 60,

            "minutos_desde_comida": 0,
            "minutos_desde_alojamiento": 0,

            "destinos_visitados": [origen],

            "vuelos": [],
            "actividades": [],
            "trabajos": [],

            "gasto_total": 0.0,
            "ganancia_total": 0.0,
        }
    # AVANZAR PASO

    def avanzar_paso(
        self,
        estado: dict,
        destino: str,
        aeronave: str,
    ) -> dict:

        origen = estado["aeropuerto_actual"]

        route = self.graph.get_route(origen, destino)

        if route is None:
            raise ValueError(
                f"No route exists from {origen} to {destino}"
            )

        if route.bloqueada:
            raise ValueError(
                f"Route {origen} -> {destino} is blocked."
            )

        aircraft = Aircraft.from_defaults(aeronave)

        costo_vuelo = aircraft.calcular_costo(
            route.distancia_km
        )

        tiempo_vuelo = aircraft.calcular_tiempo(
            route.distancia_km
        )

        if estado["presupuesto_actual"] < costo_vuelo:
            raise ValueError(
                "Insufficient budget for this flight."
            )

        if estado["tiempo_restante_min"] < tiempo_vuelo:
            raise ValueError(
                "Insufficient available time."
            )

        estado["presupuesto_actual"] -= costo_vuelo
        estado["gasto_total"] += costo_vuelo

        estado["tiempo_restante_min"] -= tiempo_vuelo

        estado["minutos_desde_comida"] += tiempo_vuelo
        estado["minutos_desde_alojamiento"] += tiempo_vuelo

        estado["vuelos"].append(
            {
                "origen": origen,
                "destino": destino,
                "aeronave": aeronave,
                "distancia_km": route.distancia_km,
                "costo": costo_vuelo,
                "tiempo_min": tiempo_vuelo,
            }
        )

        estado["aeropuerto_actual"] = destino

        if destino not in estado["destinos_visitados"]:
            estado["destinos_visitados"].append(destino)

        self._aplicar_comida(estado)
        self._aplicar_alojamiento(estado)

        return estado

    # ACTIVIDADES

    def realizar_actividad(
        self,
        estado: dict,
        actividad_nombre: str,
    ) -> dict:

        airport = self.graph.get_node(
            estado["aeropuerto_actual"]
        )

        actividad = next(
            (
                a
                for a in airport.actividades
                if a.nombre == actividad_nombre
            ),
            None,
        )

        if actividad is None:
            raise ValueError(
                f"Activity '{actividad_nombre}' not found."
            )

        if estado["presupuesto_actual"] < actividad.costo_usd:
            raise ValueError(
                "Insufficient budget."
            )

        if estado["tiempo_restante_min"] < actividad.duracion_min:
            raise ValueError(
                "Insufficient available time."
            )

        estado["presupuesto_actual"] -= actividad.costo_usd
        estado["gasto_total"] += actividad.costo_usd

        estado["tiempo_restante_min"] -= actividad.duracion_min

        estado["actividades"].append(
            {
                "nombre": actividad.nombre,
                "tipo": actividad.tipo,
                "costo": actividad.costo_usd,
                "duracion_min": actividad.duracion_min,
            }
        )

        return estado

    # TRABAJOS

    def tomar_trabajo(
        self,
        estado: dict,
        trabajo_nombre: str,
        horas: float,
    ) -> dict:

        umbral = (
            estado["presupuesto_inicial"] * 0.35
        )

        if estado["presupuesto_actual"] > umbral:
            raise ValueError(
                "Jobs are only available when budget "
                "falls below 35% of the initial budget."
            )

        airport = self.graph.get_node(
            estado["aeropuerto_actual"]
        )

        trabajo = next(
            (
                t
                for t in airport.trabajos
                if t.nombre == trabajo_nombre
            ),
            None,
        )

        if trabajo is None:
            raise ValueError(
                f"Job '{trabajo_nombre}' not found."
            )

        minutos_trabajo = horas * 60

        if estado["tiempo_restante_min"] < minutos_trabajo:
            raise ValueError(
                "Insufficient available time."
            )

        ingreso = trabajo.calcular_ingreso(horas)

        estado["presupuesto_actual"] += ingreso
        estado["ganancia_total"] += ingreso

        estado["tiempo_restante_min"] -= minutos_trabajo

        estado["trabajos"].append(
            {
                "nombre": trabajo.nombre,
                "horas": horas,
                "ingreso": ingreso,
            }
        )

        return estado

    # COSTOS AUTOMÁTICOS

    def _aplicar_comida(self, estado: dict) -> None:

        if (
            estado["minutos_desde_comida"]
            < self.COMIDA_CADA_MIN
        ):
            return

        airport = self.graph.get_node(
            estado["aeropuerto_actual"]
        )

        costo = airport.costo_alimentacion

        estado["presupuesto_actual"] -= costo
        estado["gasto_total"] += costo

        estado["minutos_desde_comida"] = 0

    def _aplicar_alojamiento(
        self,
        estado: dict,
    ) -> None:

        if (
            estado["minutos_desde_alojamiento"]
            < self.ALOJAMIENTO_CADA_MIN
        ):
            return

        airport = self.graph.get_node(
            estado["aeropuerto_actual"]
        )

        costo = airport.costo_alojamiento

        estado["presupuesto_actual"] -= costo
        estado["gasto_total"] += costo

        estado["minutos_desde_alojamiento"] = 0
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

            # Subsidized-route tracking (max 20 % of total trip distance)
            "distancia_total": 0.0,
            "distancia_subsidiada": 0.0,

            # Minimum-stay tracking at the current airport
            "tiempo_en_aeropuerto_actual": 0,
            "estancia_minima_requerida": 0,
            "tiempo_libre": 0,

            # R4: in-transit state
            "en_transito": False,
            "vuelo_en_curso": None,

            "destinos_visitados": [origen],

            # R5: per-destination detail  {IATA: {"costo_total": 0.0, "tiempo_total_min": 0}}
            "detalle_por_destino": {
                origen: {"costo_total": 0.0, "tiempo_total_min": 0},
            },

            "vuelos": [],
            "actividades": [],
            "trabajos": [],

            "gasto_total": 0.0,
            "ganancia_total": 0.0,
        }
    # AVANZAR PASO (atomic — calls iniciar_vuelo + completar_vuelo)

    def avanzar_paso(
        self,
        estado: dict,
        destino: str,
        aeronave: str,
    ) -> dict:
        self.iniciar_vuelo(estado, destino, aeronave)
        return self.completar_vuelo(estado)

    # R4: GRANULAR FLIGHT OPERATIONS

    def iniciar_vuelo(
        self,
        estado: dict,
        destino: str,
        aeronave: str,
    ) -> dict:
        """
        Begin a flight leg.  Sets en_transito=True and records vuelo_en_curso
        without moving aeropuerto_actual.  Deducts cost and time immediately.
        An interruption can be handled between this call and completar_vuelo.
        """
        if estado.get("en_transito"):
            raise ValueError(
                "Already in transit. Complete or interrupt the current "
                "flight before starting a new one."
            )

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

        costo_vuelo = (
            0.0 if route.es_subsidiada
            else aircraft.calcular_costo(route.distancia_km)
        )

        tiempo_vuelo = aircraft.calcular_tiempo(route.distancia_km)

        # ── R3: 20 % subsidized-route limit ──────────────────────────
        if route.es_subsidiada:
            max_porc = self.config.get("maxSubsidiadaPorcentaje", 20) / 100
            nueva_subsidiada = estado["distancia_subsidiada"] + route.distancia_km
            nueva_total = estado["distancia_total"] + route.distancia_km
            if nueva_subsidiada / nueva_total > max_porc:
                raise ValueError(
                    f"Subsidized route limit exceeded: subsidized distance "
                    f"cannot exceed {int(max_porc * 100)}% of total trip distance."
                )

        if estado["presupuesto_actual"] < costo_vuelo:
            raise ValueError("Insufficient budget for this flight.")

        if estado["tiempo_restante_min"] < tiempo_vuelo:
            raise ValueError("Insufficient available time.")

        # ── R3: enforce estancia mínima (auto-fill remainder as free time) ──
        tiempo_faltante = (
            estado["estancia_minima_requerida"]
            - estado["tiempo_en_aeropuerto_actual"]
        )
        if tiempo_faltante > 0:
            if estado["tiempo_restante_min"] - tiempo_faltante < tiempo_vuelo:
                raise ValueError(
                    "Insufficient time to meet minimum stay requirement "
                    "before this flight."
                )
            estado["tiempo_restante_min"] -= tiempo_faltante
            estado["tiempo_libre"] += tiempo_faltante
            estado["tiempo_en_aeropuerto_actual"] += tiempo_faltante
            estado["minutos_desde_comida"] += tiempo_faltante
            estado["minutos_desde_alojamiento"] += tiempo_faltante

        # ── R3: capture origin airport food cost before leaving ───────
        origen_node = self.graph.get_node(origen)

        estado["presupuesto_actual"] -= costo_vuelo
        estado["gasto_total"] += costo_vuelo

        estado["tiempo_restante_min"] -= tiempo_vuelo
        estado["minutos_desde_comida"] += tiempo_vuelo
        estado["minutos_desde_alojamiento"] += tiempo_vuelo

        # ── R3: accumulate trip distances ────────────────────────────
        estado["distancia_total"] += route.distancia_km
        if route.es_subsidiada:
            estado["distancia_subsidiada"] += route.distancia_km

        # ── R5: flight cost + time attributed to origin airport ──────
        self._acumular_destino(estado, origen, costo_vuelo, tiempo_vuelo)

        # ── R4: enter in-transit state ────────────────────────────────
        estado["en_transito"] = True
        estado["vuelo_en_curso"] = {
            "origen": origen,
            "destino": destino,
            "aeronave": aeronave,
            "distancia_km": route.distancia_km,
            "costo": costo_vuelo,
            "tiempo_min": tiempo_vuelo,
            "subsidiada": route.es_subsidiada,
            # Internal keys used by completar_vuelo / interruption
            "_estancia_minima": route.estancia_minima,
            "_costo_alimentacion_origen": origen_node.costo_alimentacion,
        }

        return estado

    def completar_vuelo(self, estado: dict) -> dict:
        """
        Finalise an in-progress flight leg.  Moves aeropuerto_actual to the
        destination, appends the leg to vuelos, resets stay counters and
        applies periodic meal / lodging charges.
        Raises ValueError if the traveler is not currently in transit.
        """
        if not estado.get("en_transito"):
            raise ValueError("Not currently in transit.")

        vuelo = estado["vuelo_en_curso"]

        estado["vuelos"].append(
            {
                "origen": vuelo["origen"],
                "destino": vuelo["destino"],
                "aeronave": vuelo["aeronave"],
                "distancia_km": vuelo["distancia_km"],
                "costo": vuelo["costo"],
                "tiempo_min": vuelo["tiempo_min"],
                "subsidiada": vuelo["subsidiada"],
            }
        )

        estado["aeropuerto_actual"] = vuelo["destino"]

        if vuelo["destino"] not in estado["destinos_visitados"]:
            estado["destinos_visitados"].append(vuelo["destino"])

        # ── R5: ensure destination entry exists (first arrival) ──────
        self._acumular_destino(estado, vuelo["destino"], 0.0, 0)

        # ── R3: reset stay counters for the new airport ───────────────
        estado["tiempo_en_aeropuerto_actual"] = 0
        estado["estancia_minima_requerida"] = vuelo["_estancia_minima"]

        # ── R3: meal charged at origin cost, lodge at destination ─────
        self._aplicar_comida(estado, vuelo["_costo_alimentacion_origen"])
        self._aplicar_alojamiento(estado)

        # ── R4: clear transit state ───────────────────────────────────
        estado["en_transito"] = False
        estado["vuelo_en_curso"] = None

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
        estado["tiempo_en_aeropuerto_actual"] += actividad.duracion_min

        # ── R5: attribute activity cost + time to current airport ────
        self._acumular_destino(
            estado,
            estado["aeropuerto_actual"],
            actividad.costo_usd,
            actividad.duracion_min,
        )

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

        umbral_porc = self.config.get("presupuestoMinimoPorc", 35) / 100
        umbral = estado["presupuesto_inicial"] * umbral_porc

        if estado["presupuesto_actual"] > umbral:
            raise ValueError(
                "Jobs are only available when budget falls below "
                f"{int(umbral_porc * 100)}% of the initial budget."
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
        estado["tiempo_en_aeropuerto_actual"] += minutos_trabajo

        # ── R5: attribute worked time to current airport (no cost) ───
        self._acumular_destino(
            estado,
            estado["aeropuerto_actual"],
            0.0,
            minutos_trabajo,
        )

        estado["trabajos"].append(
            {
                "nombre": trabajo.nombre,
                "horas": horas,
                "ingreso": ingreso,
            }
        )

        return estado

    # COSTOS AUTOMÁTICOS

    def _aplicar_comida(self, estado: dict, costo_alimentacion: float) -> None:
        """Charge one meal period using the origin airport's food cost."""
        if (
            estado["minutos_desde_comida"]
            < self.COMIDA_CADA_MIN
        ):
            return

        estado["presupuesto_actual"] -= costo_alimentacion
        estado["gasto_total"] += costo_alimentacion
        estado["minutos_desde_comida"] = 0

        # R5: meal cost attributed to the airport whose food cost is used
        # (the caller passes the origin airport's cost for in-flight meals)
        self._acumular_destino(
            estado,
            estado["aeropuerto_actual"],
            costo_alimentacion,
            0,
        )

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

        # R5: lodging cost attributed to current airport (destination)
        self._acumular_destino(
            estado,
            estado["aeropuerto_actual"],
            costo,
            0,
        )

        # R5: lodging cost attributed to current airport (destination)
        self._acumular_destino(
            estado,
            estado["aeropuerto_actual"],
            costo,
            0,
        )

    # R5: PER-DESTINATION ACCUMULATOR

    @staticmethod
    def _acumular_destino(
        estado: dict,
        iata: str,
        costo: float,
        tiempo_min: float,
    ) -> None:
        """Add cost and time to the per-destination ledger."""
        detalle = estado.setdefault("detalle_por_destino", {})
        entry = detalle.setdefault(iata, {"costo_total": 0.0, "tiempo_total_min": 0.0})
        entry["costo_total"] = round(entry["costo_total"] + costo, 4)
        entry["tiempo_total_min"] = round(entry["tiempo_total_min"] + tiempo_min, 4)

    # R2: ROUTE OPTIONS

    def obtener_opciones_ruta(
        self,
        origen: str,
        destino: str,
    ) -> dict:
        """
        Return all aircraft options available on a direct route, with
        their calculated cost and time using the active config rates.

        Raises:
            KeyError   : If either airport does not exist.
            ValueError : If no direct route exists between the two airports.
        """
        origen  = origen.upper()
        destino = destino.upper()

        if not self.graph.has_node(origen):
            raise KeyError(f"Airport '{origen}' not found.")
        if not self.graph.has_node(destino):
            raise KeyError(f"Airport '{destino}' not found.")

        route = self.graph.get_route(origen, destino)

        if route is None:
            raise ValueError(
                f"No direct route exists from {origen} to {destino}."
            )

        aeronaves_config = self.config.get("aeronaves", {})
        opciones = []
        for nombre in route.aeronaves:
            rates = aeronaves_config.get(nombre, {})
            costo_km  = rates.get("costo_km",  0.18)
            tiempo_km = rates.get("tiempo_km", 0.70)
            aircraft = Aircraft(nombre, costo_km, tiempo_km)
            costo_vuelo = (
                0.0
                if route.es_subsidiada
                else aircraft.calcular_costo(route.distancia_km)
            )
            opciones.append(
                {
                    "aeronave":     nombre,
                    "costo_usd":    costo_vuelo,
                    "tiempo_min":   aircraft.calcular_tiempo(route.distancia_km),
                    "subsidiada":   route.es_subsidiada,
                }
            )

        return {
            "origen":        origen,
            "destino":       destino,
            "distancia_km":  route.distancia_km,
            "bloqueada":     route.bloqueada,
            "estancia_minima": route.estancia_minima,
            "opciones":      opciones,
        }
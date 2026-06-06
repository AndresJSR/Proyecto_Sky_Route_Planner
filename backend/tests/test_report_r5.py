"""
Tests for R5 — per-destination detail in the final report.

Covers:
  1. detalle_por_destino initialised correctly in iniciar_viaje.
  2. Flight cost + time accumulates at the ORIGIN airport.
  3. Activity cost + time accumulates at the CURRENT airport.
  4. Worked time accumulates at the CURRENT airport.
  5. generar_reporte includes a 'detalle' list in destinos_visitados.
  6. Each entry has: iata, nombre, ciudad, pais, costo_total_usd,
     tiempo_total_min.
  7. Entries appear in visit order.
  8. Airport metadata (nombre, ciudad, pais) fetched from graph.
  9. Unknown airport gracefully degrades (name = iata, empty city/pais).
 10. Costs and times sum correctly across multiple events at one airport.
 11. Integration: full trip report sums match top-level gasto_total.
"""

from __future__ import annotations

import os
import pytest

from domain.models.activity import Activity
from domain.models.aircraft import Aircraft
from domain.models.airport import Airport
from domain.models.job import Job
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from infrastructure.json_loader import JSONLoader
from services.advanced_planner_service import AdvancedPlannerService
from services.report_service import ReportService


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "presupuestoMinimoPorc":   35,
    "maxSubsidiadaPorcentaje": 20,
    "intervaloAlojamiento":    20,
    "intervaloAlimentacion":   8,
    "aeronaves": {
        "Avión Comercial": {"costo_km": 0.18, "tiempo_km": 0.70},
        "Avión Regional":  {"costo_km": 0.25, "tiempo_km": 1.10},
        "Hélice":          {"costo_km": 0.12, "tiempo_km": 2.50},
    },
}


def _airport(
    iata: str,
    nombre: str = "",
    ciudad: str = "TestCity",
    pais: str = "TestCountry",
    meal: float = 10.0,
    lodge: float = 50.0,
    actividades: list | None = None,
    trabajos: list | None = None,
) -> Airport:
    return Airport(
        id=iata,
        nombre=nombre or f"Aeropuerto {iata}",
        ciudad=ciudad,
        pais=pais,
        zona_horaria="America/Bogota",
        es_hub=True,
        costo_alojamiento=lodge,
        costo_alimentacion=meal,
        actividades=actividades or [],
        trabajos=trabajos or [],
    )


def _route(
    origen: str,
    destino: str,
    km: float,
    costo_base: float = 1.0,
    aeronaves: list[str] | None = None,
    estancia_minima: int = 0,
) -> Route:
    return Route(
        origen=origen, destino=destino, distancia_km=km,
        aeronaves=aeronaves or ["Avión Comercial"],
        costo_base=costo_base, estancia_minima=estancia_minima,
    )


def _simple_chain() -> AdjacencyGraph:
    """A ─(100 km)─► B ─(100 km)─► C"""
    g = AdjacencyGraph()
    g.add_node(_airport("A", nombre="Airport Alpha", ciudad="CityA", pais="CountryA"))
    g.add_node(_airport("B", nombre="Airport Beta",  ciudad="CityB", pais="CountryB"))
    g.add_node(_airport("C", nombre="Airport Gamma", ciudad="CityC", pais="CountryC"))
    g.add_edge(_route("A", "B", 100.0))
    g.add_edge(_route("B", "C", 100.0))
    return g


# ──────────────────────────────────────────────────────────────────────────────
# 1. detalle_por_destino initialized in iniciar_viaje
# ──────────────────────────────────────────────────────────────────────────────

class TestDetalleInit:

    def test_field_present(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        assert "detalle_por_destino" in estado

    def test_origin_entry_created(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        assert "A" in estado["detalle_por_destino"]

    def test_origin_starts_at_zero(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        entry = estado["detalle_por_destino"]["A"]
        assert entry["costo_total"] == 0.0
        assert entry["tiempo_total_min"] == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# 2. Flight cost + time attributed to ORIGIN
# ──────────────────────────────────────────────────────────────────────────────

class TestFlightAttributedToOrigin:

    def test_flight_cost_goes_to_origin(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        flight_cost = Aircraft.from_defaults("Avión Comercial").calcular_costo(100.0)
        assert estado["detalle_por_destino"]["A"]["costo_total"] == pytest.approx(flight_cost)

    def test_flight_time_goes_to_origin(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        flight_time = Aircraft.from_defaults("Avión Comercial").calcular_tiempo(100.0)
        assert estado["detalle_por_destino"]["A"]["tiempo_total_min"] == pytest.approx(flight_time)

    def test_destination_created_with_zero_on_arrival(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        assert "B" in estado["detalle_por_destino"]

    def test_two_flights_each_attributed_to_own_origin(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        svc.avanzar_paso(estado, "C", "Avión Comercial")
        cost_a = Aircraft.from_defaults("Avión Comercial").calcular_costo(100.0)
        cost_b = Aircraft.from_defaults("Avión Comercial").calcular_costo(100.0)
        assert estado["detalle_por_destino"]["A"]["costo_total"] == pytest.approx(cost_a)
        assert estado["detalle_por_destino"]["B"]["costo_total"] == pytest.approx(cost_b)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Activity cost + time attributed to current airport
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityAttribution:

    def test_activity_cost_attributed_to_current_airport(self):
        actividad = Activity("Tour", "opcional", duracion_min=60, costo_usd=30.0)
        g = AdjacencyGraph()
        g.add_node(_airport("A", actividades=[actividad]))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        svc.realizar_actividad(estado, "Tour")
        assert estado["detalle_por_destino"]["A"]["costo_total"] == pytest.approx(30.0)

    def test_activity_time_attributed_to_current_airport(self):
        actividad = Activity("Tour", "opcional", duracion_min=60, costo_usd=30.0)
        g = AdjacencyGraph()
        g.add_node(_airport("A", actividades=[actividad]))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        svc.realizar_actividad(estado, "Tour")
        assert estado["detalle_por_destino"]["A"]["tiempo_total_min"] == pytest.approx(60.0)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Job time attributed to current airport
# ──────────────────────────────────────────────────────────────────────────────

class TestJobAttribution:

    def test_job_time_attributed_to_current_airport(self):
        job = Job("Cargador", tarifa_hora=5.0, max_horas=10)
        g = AdjacencyGraph()
        g.add_node(_airport("A", trabajos=[job]))
        svc = AdvancedPlannerService(g, {**DEFAULT_CONFIG, "presupuestoMinimoPorc": 100})
        estado = svc.iniciar_viaje("A", presupuesto_inicial=100.0)
        svc.tomar_trabajo(estado, "Cargador", horas=2.0)
        assert estado["detalle_por_destino"]["A"]["tiempo_total_min"] == pytest.approx(120.0)

    def test_job_does_not_add_cost(self):
        """Jobs earn money (no cost), so costo_total must not increase."""
        job = Job("Cargador", tarifa_hora=5.0, max_horas=10)
        g = AdjacencyGraph()
        g.add_node(_airport("A", trabajos=[job]))
        svc = AdvancedPlannerService(g, {**DEFAULT_CONFIG, "presupuestoMinimoPorc": 100})
        estado = svc.iniciar_viaje("A", presupuesto_inicial=100.0)
        svc.tomar_trabajo(estado, "Cargador", horas=2.0)
        assert estado["detalle_por_destino"]["A"]["costo_total"] == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# 5–9. generar_reporte structure
# ──────────────────────────────────────────────────────────────────────────────

class TestGenararReporteDetalle:

    @pytest.fixture
    def reporte(self):
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        rpt = ReportService(g)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        return rpt.generar_reporte(estado)

    def test_detalle_key_present(self, reporte):
        assert "detalle" in reporte["destinos_visitados"]

    def test_detalle_is_list(self, reporte):
        assert isinstance(reporte["destinos_visitados"]["detalle"], list)

    def test_detalle_length_matches_visited(self, reporte):
        qty = reporte["destinos_visitados"]["cantidad"]
        assert len(reporte["destinos_visitados"]["detalle"]) == qty

    def test_entry_has_required_keys(self, reporte):
        required = {"iata", "nombre", "ciudad", "pais",
                    "costo_total_usd", "tiempo_total_min"}
        for entry in reporte["destinos_visitados"]["detalle"]:
            assert required.issubset(entry.keys()), \
                f"Missing keys in {entry}"

    def test_entries_in_visit_order(self, reporte):
        iatas = [e["iata"] for e in reporte["destinos_visitados"]["detalle"]]
        assert iatas == ["A", "B"]

    def test_airport_metadata_filled(self, reporte):
        a_entry = next(e for e in reporte["destinos_visitados"]["detalle"] if e["iata"] == "A")
        assert a_entry["nombre"] == "Airport Alpha"
        assert a_entry["ciudad"] == "CityA"
        assert a_entry["pais"]   == "CountryA"

    def test_costo_and_tiempo_numeric(self, reporte):
        for entry in reporte["destinos_visitados"]["detalle"]:
            assert isinstance(entry["costo_total_usd"], (int, float))
            assert isinstance(entry["tiempo_total_min"], (int, float))

    def test_unknown_airport_graceful_degradation(self):
        """State with an IATA not in the graph must not crash."""
        g = _simple_chain()
        rpt = ReportService(g)
        fake_estado = {
            "presupuesto_inicial": 1000.0,
            "presupuesto_actual":  900.0,
            "gasto_total":         100.0,
            "ganancia_total":      0.0,
            "tiempo_total_min":    600.0,
            "tiempo_restante_min": 500.0,
            "destinos_visitados":  ["ZZZ"],
            "detalle_por_destino": {"ZZZ": {"costo_total": 10.0, "tiempo_total_min": 30.0}},
            "vuelos":      [],
            "actividades": [],
            "trabajos":    [],
        }
        reporte = rpt.generar_reporte(fake_estado)
        entry = reporte["destinos_visitados"]["detalle"][0]
        assert entry["iata"]   == "ZZZ"
        assert entry["nombre"] == "ZZZ"
        assert entry["ciudad"] == ""
        assert entry["pais"]   == ""

    def test_origin_without_any_events_has_zero_cost(self):
        """Origin airport with no flights/activities/jobs must have costo=0."""
        g = _simple_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        rpt = ReportService(g)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        reporte = rpt.generar_reporte(estado)
        a_entry = reporte["destinos_visitados"]["detalle"][0]
        assert a_entry["costo_total_usd"] == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# 10. Costs accumulate across multiple events at one airport
# ──────────────────────────────────────────────────────────────────────────────

class TestMultipleEventsAtOneAirport:

    def test_two_activities_costs_sum(self):
        act1 = Activity("Tour",   "opcional", duracion_min=60, costo_usd=30.0)
        act2 = Activity("Museo",  "opcional", duracion_min=90, costo_usd=20.0)
        g = AdjacencyGraph()
        g.add_node(_airport("A", actividades=[act1, act2]))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        svc.realizar_actividad(estado, "Tour")
        svc.realizar_actividad(estado, "Museo")
        assert estado["detalle_por_destino"]["A"]["costo_total"] == pytest.approx(50.0)

    def test_two_activities_times_sum(self):
        act1 = Activity("Tour",  "opcional", duracion_min=60, costo_usd=30.0)
        act2 = Activity("Museo", "opcional", duracion_min=90, costo_usd=20.0)
        g = AdjacencyGraph()
        g.add_node(_airport("A", actividades=[act1, act2]))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        svc.realizar_actividad(estado, "Tour")
        svc.realizar_actividad(estado, "Museo")
        assert estado["detalle_por_destino"]["A"]["tiempo_total_min"] == pytest.approx(150.0)


# ──────────────────────────────────────────────────────────────────────────────
# 11. Integration: per-destination costs sum to gasto_total
# ──────────────────────────────────────────────────────────────────────────────

class TestCostSumIntegrity:

    def test_sum_of_per_destination_costs_equals_gasto_total(self):
        """
        The sum of costo_total across all destinations must equal
        estado['gasto_total'] (within floating-point tolerance).
        """
        act = Activity("Tour", "opcional", duracion_min=30, costo_usd=15.0)
        g = AdjacencyGraph()
        g.add_node(_airport("A", meal=10.0))
        g.add_node(_airport("B", actividades=[act], meal=10.0))
        g.add_node(_airport("C", meal=10.0))
        g.add_edge(_route("A", "B", 100.0))
        g.add_edge(_route("B", "C", 100.0))

        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        rpt = ReportService(g)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        svc.realizar_actividad(estado, "Tour")
        svc.avanzar_paso(estado, "C", "Avión Comercial")

        reporte = rpt.generar_reporte(estado)
        detalle = reporte["destinos_visitados"]["detalle"]
        suma_detalle = sum(e["costo_total_usd"] for e in detalle)

        assert suma_detalle == pytest.approx(estado["gasto_total"], rel=1e-3)


# ──────────────────────────────────────────────────────────────────────────────
# 12. Integration: real network round-trip
# ──────────────────────────────────────────────────────────────────────────────

class TestRealNetworkReport:

    @pytest.fixture
    def graph_and_config(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "network.json"
        )
        graph, config = JSONLoader().load(path)
        return graph, config

    def test_report_detalle_has_entries(self, graph_and_config):
        graph, config = graph_and_config
        svc = AdvancedPlannerService(graph, config)
        rpt = ReportService(graph)
        estado = svc.iniciar_viaje("BOG", presupuesto_inicial=2000.0, tiempo_total_horas=100.0)
        svc.avanzar_paso(estado, "MDE", "Avión Comercial")
        reporte = rpt.generar_reporte(estado)
        detalle = reporte["destinos_visitados"]["detalle"]
        assert len(detalle) == 2  # BOG + MDE

    def test_report_detalle_airport_names_populated(self, graph_and_config):
        graph, config = graph_and_config
        svc = AdvancedPlannerService(graph, config)
        rpt = ReportService(graph)
        estado = svc.iniciar_viaje("BOG", presupuesto_inicial=2000.0, tiempo_total_horas=100.0)
        svc.avanzar_paso(estado, "MDE", "Avión Comercial")
        reporte = rpt.generar_reporte(estado)
        for entry in reporte["destinos_visitados"]["detalle"]:
            assert entry["nombre"] != entry["iata"], \
                f"Airport {entry['iata']} has no real name"
            assert entry["ciudad"] != ""
            assert entry["pais"] != ""

    def test_report_detalle_costs_nonnegative(self, graph_and_config):
        graph, config = graph_and_config
        svc = AdvancedPlannerService(graph, config)
        rpt = ReportService(graph)
        estado = svc.iniciar_viaje("BOG", presupuesto_inicial=2000.0, tiempo_total_horas=100.0)
        svc.avanzar_paso(estado, "MDE", "Avión Comercial")
        reporte = rpt.generar_reporte(estado)
        for entry in reporte["destinos_visitados"]["detalle"]:
            assert entry["costo_total_usd"] >= 0.0
            assert entry["tiempo_total_min"] >= 0.0

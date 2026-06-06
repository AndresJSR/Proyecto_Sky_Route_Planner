"""
Tests for R3 — Planificación avanzada (AdvancedPlannerService).

Covers the five gaps that complete R3:
  1. 20 % subsidized-route distance limit  (maxSubsidiadaPorcentaje)
  2. In-flight meal cost charged at the ORIGIN airport, not destination
  3. estanciaMinima enforcement (auto-fill remainder as free time)
  4. Free-time accumulation (tiempo_libre)
  5. Config-driven job-availability threshold (presupuestoMinimoPorc)

Each class is self-contained: it builds its own minimal AdjacencyGraph so
tests do not depend on the real network file.
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
    meal: float = 10.0,
    lodge: float = 50.0,
    trabajos: list | None = None,
    actividades: list | None = None,
) -> Airport:
    return Airport(
        id=iata,
        nombre=f"Airport {iata}",
        ciudad="TestCity",
        pais="TestCountry",
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
    """costo_base=0 → subsidised; costo_base≥1 → normal."""
    return Route(
        origen=origen,
        destino=destino,
        distancia_km=km,
        aeronaves=aeronaves or ["Avión Comercial"],
        costo_base=costo_base,
        estancia_minima=estancia_minima,
    )


def _service(config: dict | None = None) -> AdvancedPlannerService:
    """Return a service instance with an empty graph (graph added per test)."""
    return AdvancedPlannerService(AdjacencyGraph(), config or DEFAULT_CONFIG)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Subsidized-route limit (20 %)
# ──────────────────────────────────────────────────────────────────────────────

class TestSubsidizedRouteLimit:
    """
    The traveler may not use subsidised routes for more than 20 % of the
    total accumulated trip distance.  Each subsidised leg is checked before
    it is committed to the state.
    """

    @staticmethod
    def _make_graph() -> AdjacencyGraph:
        """
        A ─(4 000 km, normal)──► B ─(600 km, sub)──► C ─(600 km, sub)──► D

        After A→B : total=4 000, sub=0   → 0 %
        After B→C : total=4 600, sub=600 → 13 % ≤ 20 % ✓
        After C→D : total=5 200, sub=1200 → 23 % > 20 % ✗
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C", "D"):
            g.add_node(_airport(iata))
        g.add_edge(_route("A", "B", 4000.0, costo_base=1.0))
        g.add_edge(_route("B", "C",  600.0, costo_base=0.0))  # subsidised
        g.add_edge(_route("C", "D",  600.0, costo_base=0.0))  # subsidised
        return g

    def test_subsidized_first_leg_always_blocked(self):
        """First leg is subsidised → ratio = 100 % > 20 % → must raise."""
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        g.add_edge(_route("A", "B", 600.0, costo_base=0.0))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        with pytest.raises(ValueError, match="Subsidized route limit exceeded"):
            svc.avanzar_paso(estado, "B", "Avión Comercial")

    def test_subsidized_leg_allowed_within_limit(self):
        """After 4 000 km non-sub, a 600 km sub leg (13 %) is allowed."""
        g = self._make_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")    # non-sub A→B
        svc.avanzar_paso(estado, "C", "Avión Comercial")    # sub B→C (13 %) ✓
        assert estado["distancia_subsidiada"] == pytest.approx(600.0)
        assert estado["distancia_total"] == pytest.approx(4600.0)

    def test_subsidized_leg_blocked_when_limit_exceeded(self):
        """Third leg (C→D sub) would bring ratio to 23 % → must raise."""
        g = self._make_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")    # non-sub
        svc.avanzar_paso(estado, "C", "Avión Comercial")    # sub 13 % ✓
        with pytest.raises(ValueError, match="Subsidized route limit exceeded"):
            svc.avanzar_paso(estado, "D", "Avión Comercial")   # sub 23 % ✗

    def test_config_override_custom_limit(self):
        """maxSubsidiadaPorcentaje=30 in config → 23 % sub leg is now allowed."""
        config = {**DEFAULT_CONFIG, "maxSubsidiadaPorcentaje": 30}
        g = self._make_graph()
        svc = AdvancedPlannerService(g, config)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")   # non-sub
        svc.avanzar_paso(estado, "C", "Avión Comercial")   # sub 13 %
        svc.avanzar_paso(estado, "D", "Avión Comercial")   # sub 23 % < 30 % ✓
        assert estado["distancia_subsidiada"] == pytest.approx(1200.0)

    def test_subsidized_flight_costs_zero(self):
        """A subsidised leg must not deduct any flight cost from the budget."""
        g = self._make_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")  # non-sub ($720)
        budget_before = estado["presupuesto_actual"]
        svc.avanzar_paso(estado, "C", "Avión Comercial")  # sub → $0
        assert estado["presupuesto_actual"] == pytest.approx(budget_before)

    def test_distances_tracked_for_non_subsidized_legs(self):
        """distancia_total grows by leg distance; distancia_subsidiada stays 0."""
        g = self._make_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        assert estado["distancia_total"] == pytest.approx(4000.0)
        assert estado["distancia_subsidiada"] == pytest.approx(0.0)

    def test_vuelo_record_includes_subsidiada_flag(self):
        """Each entry in estado['vuelos'] must carry the 'subsidiada' flag."""
        g = self._make_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        svc.avanzar_paso(estado, "C", "Avión Comercial")
        assert estado["vuelos"][0]["subsidiada"] is False
        assert estado["vuelos"][1]["subsidiada"] is True


# ──────────────────────────────────────────────────────────────────────────────
# 2. In-flight meal cost charged at origin airport
# ──────────────────────────────────────────────────────────────────────────────

class TestMealCostDuringFlight:
    """
    If ≥ 480 minutes elapse during a flight the meal cost must be charged
    using the ORIGIN airport's costo_alimentacion (the traveler ate their
    last meal there), not the destination's.
    """

    # Hélice: 2.5 min/km → 200 km = 500 min > 480 min (triggers one meal)
    FLIGHT_KM = 200.0

    @staticmethod
    def _make_graph(origin_meal: float, dest_meal: float) -> AdjacencyGraph:
        g = AdjacencyGraph()
        g.add_node(_airport("A", meal=origin_meal))
        g.add_node(_airport("B", meal=dest_meal))
        g.add_edge(_route("A", "B", TestMealCostDuringFlight.FLIGHT_KM,
                          aeronaves=["Hélice"]))
        return g

    def test_meal_charged_at_origin_cost(self):
        """Meal triggered during flight uses origin airport's cost (10), not dest (50)."""
        g = self._make_graph(origin_meal=10.0, dest_meal=50.0)
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)

        flight_cost = Aircraft.from_defaults("Hélice").calcular_costo(self.FLIGHT_KM)
        svc.avanzar_paso(estado, "B", "Hélice")

        expected_deduction = flight_cost + 10.0   # flight + origin meal
        assert estado["gasto_total"] == pytest.approx(expected_deduction)

    def test_meal_not_charged_at_dest_cost(self):
        """When origin meal=10 and dest meal=50, gasto_total must NOT include 50."""
        g = self._make_graph(origin_meal=10.0, dest_meal=50.0)
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)

        flight_cost = Aircraft.from_defaults("Hélice").calcular_costo(self.FLIGHT_KM)
        svc.avanzar_paso(estado, "B", "Hélice")

        wrong_deduction = flight_cost + 50.0
        assert estado["gasto_total"] != pytest.approx(wrong_deduction)

    def test_no_meal_on_short_flight(self):
        """A 10-minute flight (< 480 min) must not trigger a meal charge."""
        g = AdjacencyGraph()
        g.add_node(_airport("A", meal=10.0))
        g.add_node(_airport("B", meal=50.0))
        g.add_edge(_route("A", "B", 10.0, aeronaves=["Avión Comercial"]))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)

        flight_cost = Aircraft.from_defaults("Avión Comercial").calcular_costo(10.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")

        assert estado["gasto_total"] == pytest.approx(flight_cost)

    def test_meal_counter_resets_after_charge(self):
        """After a meal is charged, minutos_desde_comida should reset to 0."""
        g = self._make_graph(origin_meal=10.0, dest_meal=50.0)
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Hélice")
        assert estado["minutos_desde_comida"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# 3 & 4. estanciaMinima enforcement + free-time tracking
# ──────────────────────────────────────────────────────────────────────────────

class TestEstanciaMinima:
    """
    When a traveler has not yet satisfied the minimum stay (estanciaMinima)
    at the current airport, the service must:
      a) auto-consume the remaining time as 'tiempo libre',
      b) accumulate it in estado['tiempo_libre'],
      c) raise ValueError if total available time is insufficient.

    The origin airport starts with estancia_minima_requerida = 0 so the
    traveler can fly out immediately on the first step.
    """

    ESTANCIA = 120   # minutes required at destination

    @staticmethod
    def _make_chain(estancia_minima: int = 120) -> AdjacencyGraph:
        """A ─► B(estancia=120) ─► C(estancia=0)"""
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        g.add_node(_airport("C"))
        g.add_edge(_route("A", "B", 50.0, estancia_minima=estancia_minima))
        g.add_edge(_route("B", "C", 50.0, estancia_minima=0))
        return g

    def test_origin_has_no_minimum_stay(self):
        """First flight from origin must succeed with no stay required."""
        g = self._make_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")   # no minimum at origin
        assert estado["aeropuerto_actual"] == "B"

    def test_estancia_not_met_auto_fills_free_time(self):
        """Activity covers 60 of 120 min; flying out auto-adds 60 min free time."""
        g = self._make_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")

        # Manually simulate 60 min of airport time (e.g., from an activity)
        estado["tiempo_en_aeropuerto_actual"] = 60

        svc.avanzar_paso(estado, "C", "Avión Comercial")
        assert estado["tiempo_libre"] == 60

    def test_estancia_fully_met_no_free_time_added(self):
        """When 120 min of activity fills the minimum, free time stays 0."""
        g = self._make_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")

        estado["tiempo_en_aeropuerto_actual"] = 120   # exactly meets minimum

        svc.avanzar_paso(estado, "C", "Avión Comercial")
        assert estado["tiempo_libre"] == 0

    def test_estancia_raises_when_time_insufficient(self):
        """Not enough time to fill stay + flight → ValueError."""
        g = self._make_chain(estancia_minima=10_000)   # huge minimum stay
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=5.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        with pytest.raises(ValueError, match="minimum stay"):
            svc.avanzar_paso(estado, "C", "Avión Comercial")

    def test_free_time_consumes_tiempo_restante(self):
        """Auto-filled free time must reduce tiempo_restante_min."""
        g = self._make_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")

        tiempo_before = estado["tiempo_restante_min"]
        estado["tiempo_en_aeropuerto_actual"] = 0  # 120 min of free time needed

        svc.avanzar_paso(estado, "C", "Avión Comercial")
        flight_b_c = Aircraft.from_defaults("Avión Comercial").calcular_tiempo(50.0)
        expected = tiempo_before - 120 - flight_b_c
        assert estado["tiempo_restante_min"] == pytest.approx(expected)

    def test_estancia_minima_set_after_landing(self):
        """After landing at B, estancia_minima_requerida equals route.estancia_minima."""
        g = self._make_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        assert estado["estancia_minima_requerida"] == 0
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        assert estado["estancia_minima_requerida"] == self.ESTANCIA

    def test_tiempo_en_aeropuerto_resets_after_flight(self):
        """After each flight, tiempo_en_aeropuerto_actual must reset to 0."""
        g = self._make_chain()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        estado["tiempo_en_aeropuerto_actual"] = 999  # simulate prior activity
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        assert estado["tiempo_en_aeropuerto_actual"] == 0

    def test_realizar_actividad_accumulates_airport_time(self):
        """realizar_actividad must add duration to tiempo_en_aeropuerto_actual."""
        actividad = Activity("Tour", "opcional", duracion_min=90, costo_usd=20.0)
        g = AdjacencyGraph()
        g.add_node(_airport("A", actividades=[actividad]))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.realizar_actividad(estado, "Tour")
        assert estado["tiempo_en_aeropuerto_actual"] == 90

    def test_tomar_trabajo_accumulates_airport_time(self):
        """tomar_trabajo must add worked minutes to tiempo_en_aeropuerto_actual."""
        job = Job("Cargador", tarifa_hora=5.0, max_horas=10)
        g = AdjacencyGraph()
        g.add_node(_airport("A", trabajos=[job]))
        svc = AdvancedPlannerService(g, {**DEFAULT_CONFIG, "presupuestoMinimoPorc": 100})
        estado = svc.iniciar_viaje("A", presupuesto_inicial=100.0, tiempo_total_horas=200.0)
        svc.tomar_trabajo(estado, "Cargador", horas=2.0)
        assert estado["tiempo_en_aeropuerto_actual"] == 120   # 2h × 60 min


# ──────────────────────────────────────────────────────────────────────────────
# 5. Config-driven job-availability threshold
# ──────────────────────────────────────────────────────────────────────────────

class TestConfigDrivenThreshold:
    """
    The minimum budget threshold for job availability must come from
    config['presupuestoMinimoPorc'], not from the hardcoded 35 % value.
    """

    @staticmethod
    def _airport_with_job() -> Airport:
        job = Job("Cargador", tarifa_hora=10.0, max_horas=8)
        return _airport("A", trabajos=[job])

    def test_default_35pct_threshold_blocks_at_40pct(self):
        """At 40 % of initial budget and default 35 % threshold, job is blocked."""
        g = AdjacencyGraph()
        g.add_node(self._airport_with_job())
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)   # 35 %
        estado = svc.iniciar_viaje("A", presupuesto_inicial=1000.0, tiempo_total_horas=200.0)
        estado["presupuesto_actual"] = 400.0  # 40 % > 35 % → blocked
        with pytest.raises(ValueError, match="35%"):
            svc.tomar_trabajo(estado, "Cargador", horas=1.0)

    def test_default_35pct_threshold_allows_at_30pct(self):
        """At 30 % of initial budget, job must be available under default 35 % threshold."""
        g = AdjacencyGraph()
        g.add_node(self._airport_with_job())
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=1000.0, tiempo_total_horas=200.0)
        estado["presupuesto_actual"] = 300.0  # 30 % ≤ 35 % → allowed
        svc.tomar_trabajo(estado, "Cargador", horas=1.0)
        assert estado["ganancia_total"] > 0

    def test_config_20pct_blocks_at_25pct(self):
        """Custom 20 % threshold: at 25 % budget job is blocked."""
        config = {**DEFAULT_CONFIG, "presupuestoMinimoPorc": 20}
        g = AdjacencyGraph()
        g.add_node(self._airport_with_job())
        svc = AdvancedPlannerService(g, config)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=1000.0, tiempo_total_horas=200.0)
        estado["presupuesto_actual"] = 250.0  # 25 % > 20 % → blocked
        with pytest.raises(ValueError, match="20%"):
            svc.tomar_trabajo(estado, "Cargador", horas=1.0)

    def test_config_20pct_allows_at_15pct(self):
        """Custom 20 % threshold: at 15 % budget job is allowed."""
        config = {**DEFAULT_CONFIG, "presupuestoMinimoPorc": 20}
        g = AdjacencyGraph()
        g.add_node(self._airport_with_job())
        svc = AdvancedPlannerService(g, config)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=1000.0, tiempo_total_horas=200.0)
        estado["presupuesto_actual"] = 150.0  # 15 % ≤ 20 % → allowed
        svc.tomar_trabajo(estado, "Cargador", horas=1.0)
        assert estado["ganancia_total"] > 0

    def test_config_50pct_allows_at_40pct(self):
        """Custom 50 % threshold: at 40 % budget (normally blocked at 35 %) job is allowed."""
        config = {**DEFAULT_CONFIG, "presupuestoMinimoPorc": 50}
        g = AdjacencyGraph()
        g.add_node(self._airport_with_job())
        svc = AdvancedPlannerService(g, config)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=1000.0, tiempo_total_horas=200.0)
        estado["presupuesto_actual"] = 400.0  # 40 % ≤ 50 % → allowed
        svc.tomar_trabajo(estado, "Cargador", horas=1.0)
        assert estado["ganancia_total"] > 0


# ──────────────────────────────────────────────────────────────────────────────
# Integration: new state fields present in iniciar_viaje
# ──────────────────────────────────────────────────────────────────────────────

class TestIniciarViajeStateFields:
    """Verify that all new R3 fields are present and initialised correctly."""

    EXPECTED_NEW_FIELDS = {
        "distancia_total",
        "distancia_subsidiada",
        "tiempo_en_aeropuerto_actual",
        "estancia_minima_requerida",
        "tiempo_libre",
    }

    @pytest.fixture
    def estado(self):
        g = AdjacencyGraph()
        g.add_node(_airport("BOG"))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        return svc.iniciar_viaje("BOG", presupuesto_inicial=1000.0)

    def test_new_fields_present(self, estado):
        for field in self.EXPECTED_NEW_FIELDS:
            assert field in estado, f"Missing state field: {field}"

    def test_distances_zero_at_start(self, estado):
        assert estado["distancia_total"] == 0.0
        assert estado["distancia_subsidiada"] == 0.0

    def test_stay_counters_zero_at_start(self, estado):
        assert estado["tiempo_en_aeropuerto_actual"] == 0
        assert estado["estancia_minima_requerida"] == 0
        assert estado["tiempo_libre"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# Integration: JSON loader exposes maxSubsidiadaPorcentaje
# ──────────────────────────────────────────────────────────────────────────────

class TestJsonLoaderSubsidizedConfig:

    @pytest.fixture
    def config(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "network.json"
        )
        _, cfg = JSONLoader().load(path)
        return cfg

    def test_max_subsidiada_key_present(self, config):
        assert "maxSubsidiadaPorcentaje" in config

    def test_max_subsidiada_default_value(self, config):
        assert config["maxSubsidiadaPorcentaje"] == 20

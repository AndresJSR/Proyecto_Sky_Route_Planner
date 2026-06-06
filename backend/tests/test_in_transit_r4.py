"""
Tests for R4 — in-transit state (AdvancedPlannerService + InterruptionService).

Covers:
  1. iniciar_viaje includes en_transito=False and vuelo_en_curso=None.
  2. iniciar_vuelo enters in-transit state (deducts cost/time, does NOT
     change aeropuerto_actual or append to vuelos).
  3. completar_vuelo finishes the flight (moves airport, appends vuelo,
     clears transit).
  4. avanzar_paso is still atomic and backward-compatible.
  5. Guard rails: cannot start a second flight while in transit; cannot
     complete a flight when not in transit.
  6. manejar_interrupcion_en_transito returns traveler to origin, refunds
     cost and time, clears transit state.
  7. Integration: block route after iniciar_vuelo → interrupt → traveler
     can fly a different route.
"""

from __future__ import annotations

import pytest

from domain.models.aircraft import Aircraft
from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from services.advanced_planner_service import AdvancedPlannerService
from services.basic_planner_service import BasicPlannerService
from services.interruption_service import InterruptionService


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


def _airport(iata: str, meal: float = 10.0, lodge: float = 50.0) -> Airport:
    return Airport(
        id=iata, nombre=f"Airport {iata}", ciudad="City",
        pais="Country", zona_horaria="America/Bogota",
        es_hub=True, costo_alojamiento=lodge, costo_alimentacion=meal,
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


def _simple_graph() -> AdjacencyGraph:
    """A(origin) ─► B ─► C"""
    g = AdjacencyGraph()
    g.add_node(_airport("A"))
    g.add_node(_airport("B"))
    g.add_node(_airport("C"))
    g.add_edge(_route("A", "B", 200.0))
    g.add_edge(_route("B", "C", 200.0))
    return g


def _fork_graph() -> AdjacencyGraph:
    """A ─► B and A ─► C (two routes from origin, for interruption tests)"""
    g = AdjacencyGraph()
    g.add_node(_airport("A"))
    g.add_node(_airport("B"))
    g.add_node(_airport("C"))
    g.add_edge(_route("A", "B", 200.0))
    g.add_edge(_route("A", "C", 300.0))
    return g


# ──────────────────────────────────────────────────────────────────────────────
# 1. State initialization
# ──────────────────────────────────────────────────────────────────────────────

class TestInTransitStateInit:

    def test_en_transito_false_at_start(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        assert estado["en_transito"] is False

    def test_vuelo_en_curso_none_at_start(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        assert estado["vuelo_en_curso"] is None


# ──────────────────────────────────────────────────────────────────────────────
# 2. iniciar_vuelo
# ──────────────────────────────────────────────────────────────────────────────

class TestIniciarVuelo:

    @pytest.fixture
    def svc_and_estado(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        return svc, estado

    def test_sets_en_transito_true(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        assert estado["en_transito"] is True

    def test_sets_vuelo_en_curso(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        assert estado["vuelo_en_curso"] is not None
        vuelo = estado["vuelo_en_curso"]
        assert vuelo["origen"] == "A"
        assert vuelo["destino"] == "B"
        assert vuelo["aeronave"] == "Avión Comercial"
        assert vuelo["distancia_km"] == pytest.approx(200.0)

    def test_does_not_change_aeropuerto_actual(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        assert estado["aeropuerto_actual"] == "A"

    def test_does_not_append_to_vuelos(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        assert len(estado["vuelos"]) == 0

    def test_does_not_update_destinos_visitados(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        assert estado["destinos_visitados"] == ["A"]

    def test_deducts_flight_cost(self, svc_and_estado):
        svc, estado = svc_and_estado
        presupuesto_antes = estado["presupuesto_actual"]
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        flight_cost = Aircraft.from_defaults("Avión Comercial").calcular_costo(200.0)
        assert estado["presupuesto_actual"] == pytest.approx(presupuesto_antes - flight_cost)

    def test_deducts_flight_time(self, svc_and_estado):
        svc, estado = svc_and_estado
        tiempo_antes = estado["tiempo_restante_min"]
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        flight_time = Aircraft.from_defaults("Avión Comercial").calcular_tiempo(200.0)
        assert estado["tiempo_restante_min"] == pytest.approx(tiempo_antes - flight_time)

    def test_accumulates_distancia_total(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        assert estado["distancia_total"] == pytest.approx(200.0)

    def test_raises_if_already_in_transit(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        with pytest.raises(ValueError, match="Already in transit"):
            svc.iniciar_vuelo(estado, "B", "Avión Comercial")

    def test_raises_on_blocked_route(self, svc_and_estado):
        svc, estado = svc_and_estado
        svc.graph.block_route("A", "B")
        with pytest.raises(ValueError, match="blocked"):
            svc.iniciar_vuelo(estado, "B", "Avión Comercial")

    def test_raises_on_insufficient_budget(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=0.01)
        with pytest.raises(ValueError, match="budget"):
            svc.iniciar_vuelo(estado, "B", "Avión Comercial")


# ──────────────────────────────────────────────────────────────────────────────
# 3. completar_vuelo
# ──────────────────────────────────────────────────────────────────────────────

class TestCompletarVuelo:

    @pytest.fixture
    def in_transit(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        return svc, estado

    def test_updates_aeropuerto_actual(self, in_transit):
        svc, estado = in_transit
        svc.completar_vuelo(estado)
        assert estado["aeropuerto_actual"] == "B"

    def test_appends_to_vuelos(self, in_transit):
        svc, estado = in_transit
        svc.completar_vuelo(estado)
        assert len(estado["vuelos"]) == 1
        assert estado["vuelos"][0]["origen"] == "A"
        assert estado["vuelos"][0]["destino"] == "B"

    def test_vuelo_record_has_no_internal_keys(self, in_transit):
        svc, estado = in_transit
        svc.completar_vuelo(estado)
        vuelo_record = estado["vuelos"][0]
        assert "_estancia_minima" not in vuelo_record
        assert "_costo_alimentacion_origen" not in vuelo_record

    def test_updates_destinos_visitados(self, in_transit):
        svc, estado = in_transit
        svc.completar_vuelo(estado)
        assert "B" in estado["destinos_visitados"]

    def test_clears_en_transito(self, in_transit):
        svc, estado = in_transit
        svc.completar_vuelo(estado)
        assert estado["en_transito"] is False

    def test_clears_vuelo_en_curso(self, in_transit):
        svc, estado = in_transit
        svc.completar_vuelo(estado)
        assert estado["vuelo_en_curso"] is None

    def test_raises_when_not_in_transit(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0)
        with pytest.raises(ValueError, match="Not currently in transit"):
            svc.completar_vuelo(estado)

    def test_sets_estancia_minima_requerida(self):
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        g.add_edge(_route("A", "B", 200.0, estancia_minima=90))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        svc.completar_vuelo(estado)
        assert estado["estancia_minima_requerida"] == 90

    def test_resets_tiempo_en_aeropuerto(self, in_transit):
        svc, estado = in_transit
        svc.completar_vuelo(estado)
        assert estado["tiempo_en_aeropuerto_actual"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# 4. avanzar_paso backward compatibility
# ──────────────────────────────────────────────────────────────────────────────

class TestAvanzarPasoBackwardCompat:

    def test_moves_to_destination_atomically(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        assert estado["aeropuerto_actual"] == "B"

    def test_appends_vuelo_record(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        assert len(estado["vuelos"]) == 1

    def test_leaves_no_transit_state(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        assert estado["en_transito"] is False
        assert estado["vuelo_en_curso"] is None

    def test_chain_of_two_steps(self):
        g = _simple_graph()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado = svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc.avanzar_paso(estado, "B", "Avión Comercial")
        svc.avanzar_paso(estado, "C", "Avión Comercial")
        assert estado["aeropuerto_actual"] == "C"
        assert len(estado["vuelos"]) == 2


# ──────────────────────────────────────────────────────────────────────────────
# 5. manejar_interrupcion_en_transito
# ──────────────────────────────────────────────────────────────────────────────

class TestManejarInterrupcionEnTransito:

    @pytest.fixture
    def svc_interruption_estado(self):
        g = _fork_graph()
        adv_svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        basic_svc = BasicPlannerService(g, DEFAULT_CONFIG)
        int_svc = InterruptionService(g, basic_svc)
        estado = adv_svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        return adv_svc, int_svc, estado

    def test_returns_not_redirected_when_not_in_transit(self, svc_interruption_estado):
        _, int_svc, estado = svc_interruption_estado
        result = int_svc.manejar_interrupcion_en_transito(estado)
        assert result["redirigido"] is False

    def test_redirected_true_when_in_transit(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        result = int_svc.manejar_interrupcion_en_transito(estado)
        assert result["redirigido"] is True

    def test_returns_traveler_to_origin(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["aeropuerto_actual"] == "A"

    def test_refunds_flight_cost(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        presupuesto_before = estado["presupuesto_actual"]
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["presupuesto_actual"] == pytest.approx(presupuesto_before)

    def test_refunds_flight_time(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        tiempo_before = estado["tiempo_restante_min"]
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["tiempo_restante_min"] == pytest.approx(tiempo_before)

    def test_refunds_gasto_total(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["gasto_total"] == pytest.approx(0.0)

    def test_undoes_distancia_total(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["distancia_total"] == pytest.approx(0.0)

    def test_clears_en_transito(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["en_transito"] is False

    def test_clears_vuelo_en_curso(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["vuelo_en_curso"] is None

    def test_result_contains_aeropuerto_retorno(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        result = int_svc.manejar_interrupcion_en_transito(estado)
        assert result["aeropuerto_retorno"] == "A"

    def test_vuelos_list_not_appended_on_interrupt(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert len(estado["vuelos"]) == 0

    def test_destinos_visitados_unchanged_on_interrupt(self, svc_interruption_estado):
        adv_svc, int_svc, estado = svc_interruption_estado
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)
        assert estado["destinos_visitados"] == ["A"]


# ──────────────────────────────────────────────────────────────────────────────
# 6. Integration: route blocked mid-flight → redirect → fly alternative
# ──────────────────────────────────────────────────────────────────────────────

class TestInTransitIntegration:

    def test_block_route_mid_flight_then_fly_alternative(self):
        """
        Full scenario:
          1. Start flight A→B (route open).
          2. Route A→B gets blocked while in transit.
          3. Interrupt → traveler back at A.
          4. Traveler takes alternative route A→C instead.
        """
        g = _fork_graph()
        adv_svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        basic_svc = BasicPlannerService(g, DEFAULT_CONFIG)
        int_svc = InterruptionService(g, basic_svc)

        estado = adv_svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)

        # 1. Begin flight A→B
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        assert estado["en_transito"] is True

        # 2. Route A→B is blocked while traveler is in the air
        int_svc.bloquear_ruta("A", "B")

        # 3. Interrupt: traveler redirected to A
        result = int_svc.manejar_interrupcion_en_transito(estado)
        assert result["redirigido"] is True
        assert estado["aeropuerto_actual"] == "A"
        assert estado["en_transito"] is False

        # 4. Fly alternative A→C (unblocked)
        adv_svc.avanzar_paso(estado, "C", "Avión Comercial")
        assert estado["aeropuerto_actual"] == "C"
        assert len(estado["vuelos"]) == 1
        assert estado["vuelos"][0]["destino"] == "C"

    def test_completar_vuelo_raises_after_interrupt(self):
        """After interrupt, completar_vuelo must raise (no longer in transit)."""
        g = _fork_graph()
        adv_svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        basic_svc = BasicPlannerService(g, DEFAULT_CONFIG)
        int_svc = InterruptionService(g, basic_svc)

        estado = adv_svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        adv_svc.iniciar_vuelo(estado, "B", "Avión Comercial")
        int_svc.manejar_interrupcion_en_transito(estado)

        with pytest.raises(ValueError, match="Not currently in transit"):
            adv_svc.completar_vuelo(estado)

    def test_subsidized_distance_refunded_on_interrupt(self):
        """If the interrupted flight was subsidised, distancia_subsidiada is restored."""
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        # non-sub first leg to avoid first-leg 100% sub ratio
        g.add_edge(_route("A", "B", 4000.0, costo_base=0.0))

        # Use a non-sub first leg so we can fly a subsidised one after
        g2 = AdjacencyGraph()
        g2.add_node(_airport("A"))
        g2.add_node(_airport("B"))
        g2.add_node(_airport("C"))
        g2.add_edge(_route("A", "B", 4000.0, costo_base=1.0))
        g2.add_edge(_route("B", "C",  600.0, costo_base=0.0))  # subsidised

        adv_svc = AdvancedPlannerService(g2, DEFAULT_CONFIG)
        basic_svc = BasicPlannerService(g2, DEFAULT_CONFIG)
        int_svc = InterruptionService(g2, basic_svc)

        estado = adv_svc.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        adv_svc.avanzar_paso(estado, "B", "Avión Comercial")  # non-sub A→B

        distancia_before = estado["distancia_total"]
        sub_before = estado["distancia_subsidiada"]

        adv_svc.iniciar_vuelo(estado, "C", "Avión Comercial")  # sub B→C
        int_svc.manejar_interrupcion_en_transito(estado)

        assert estado["distancia_total"] == pytest.approx(distancia_before)
        assert estado["distancia_subsidiada"] == pytest.approx(sub_before)

    def test_normal_iniciar_completar_roundtrip(self):
        """iniciar_vuelo + completar_vuelo equals one avanzar_paso in net effect."""
        g = _simple_graph()

        # Reference: use avanzar_paso
        svc_ref = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado_ref = svc_ref.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc_ref.avanzar_paso(estado_ref, "B", "Avión Comercial")

        # Under test: use iniciar_vuelo + completar_vuelo
        svc_ut = AdvancedPlannerService(g, DEFAULT_CONFIG)
        estado_ut = svc_ut.iniciar_viaje("A", presupuesto_inicial=5000.0, tiempo_total_horas=200.0)
        svc_ut.iniciar_vuelo(estado_ut, "B", "Avión Comercial")
        svc_ut.completar_vuelo(estado_ut)

        assert estado_ut["aeropuerto_actual"] == estado_ref["aeropuerto_actual"]
        assert estado_ut["presupuesto_actual"] == pytest.approx(estado_ref["presupuesto_actual"])
        assert estado_ut["tiempo_restante_min"] == pytest.approx(estado_ref["tiempo_restante_min"])
        assert estado_ut["gasto_total"] == pytest.approx(estado_ref["gasto_total"])
        assert len(estado_ut["vuelos"]) == len(estado_ref["vuelos"])

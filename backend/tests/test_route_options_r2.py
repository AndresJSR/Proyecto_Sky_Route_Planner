"""
Tests for R2 — GET /planner/advanced/route-options
(AdvancedPlannerService.obtener_opciones_ruta)

Covers:
  1. Returns correct top-level structure.
  2. Lists all aircraft available on the route.
  3. Cost and time computed using config rates (not hardcoded defaults).
  4. Subsidised route → costo_usd == 0 for all options.
  5. Blocked route is returned with bloqueada=True (still shows options).
  6. Non-existent airport raises KeyError.
  7. No direct route raises ValueError.
  8. estancia_minima is included in the response.
  9. Integration against the real network.
"""

from __future__ import annotations

import os
import pytest

from domain.models.airport import Airport
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


def _airport(iata: str) -> Airport:
    return Airport(
        id=iata, nombre=f"Airport {iata}", ciudad="City",
        pais="Country", zona_horaria="America/Bogota",
        es_hub=True, costo_alojamiento=50.0, costo_alimentacion=10.0,
    )


def _route(
    origen: str,
    destino: str,
    km: float,
    aeronaves: list[str],
    costo_base: float = 1.0,
    estancia_minima: int = 60,
) -> Route:
    return Route(
        origen=origen, destino=destino, distancia_km=km,
        aeronaves=aeronaves, costo_base=costo_base,
        estancia_minima=estancia_minima,
    )


def _graph_multi_aircraft() -> AdjacencyGraph:
    """A ─(500 km, Avión Comercial + Avión Regional + Hélice)─► B"""
    g = AdjacencyGraph()
    g.add_node(_airport("A"))
    g.add_node(_airport("B"))
    g.add_edge(_route("A", "B", 500.0,
                      ["Avión Comercial", "Avión Regional", "Hélice"],
                      estancia_minima=90))
    return g


# ──────────────────────────────────────────────────────────────────────────────
# 1. Top-level structure
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteOptionsStructure:

    @pytest.fixture
    def result(self):
        g = _graph_multi_aircraft()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        return svc.obtener_opciones_ruta("A", "B")

    def test_required_keys_present(self, result):
        assert {"origen", "destino", "distancia_km",
                "bloqueada", "estancia_minima", "opciones"} <= result.keys()

    def test_origen_destino_uppercase(self, result):
        assert result["origen"]  == "A"
        assert result["destino"] == "B"

    def test_distancia_km_correct(self, result):
        assert result["distancia_km"] == pytest.approx(500.0)

    def test_bloqueada_false_by_default(self, result):
        assert result["bloqueada"] is False

    def test_estancia_minima_present(self, result):
        assert result["estancia_minima"] == 90

    def test_opciones_is_list(self, result):
        assert isinstance(result["opciones"], list)

    def test_lowercase_input_normalised(self):
        g = _graph_multi_aircraft()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        result = svc.obtener_opciones_ruta("a", "b")
        assert result["origen"]  == "A"
        assert result["destino"] == "B"


# ──────────────────────────────────────────────────────────────────────────────
# 2. Aircraft options
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteOptionsAircraft:

    @pytest.fixture
    def result(self):
        g = _graph_multi_aircraft()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        return svc.obtener_opciones_ruta("A", "B")

    def test_correct_number_of_options(self, result):
        assert len(result["opciones"]) == 3

    def test_option_keys_present(self, result):
        for opt in result["opciones"]:
            assert {"aeronave", "costo_usd", "tiempo_min", "subsidiada"} <= opt.keys()

    def test_aircraft_names_match_route(self, result):
        names = {opt["aeronave"] for opt in result["opciones"]}
        assert names == {"Avión Comercial", "Avión Regional", "Hélice"}

    def test_costs_computed_correctly(self, result):
        by_name = {opt["aeronave"]: opt for opt in result["opciones"]}
        assert by_name["Avión Comercial"]["costo_usd"]  == pytest.approx(500 * 0.18)
        assert by_name["Avión Regional"]["costo_usd"]   == pytest.approx(500 * 0.25)
        assert by_name["Hélice"]["costo_usd"]           == pytest.approx(500 * 0.12)

    def test_times_computed_correctly(self, result):
        by_name = {opt["aeronave"]: opt for opt in result["opciones"]}
        assert by_name["Avión Comercial"]["tiempo_min"] == pytest.approx(500 * 0.70)
        assert by_name["Avión Regional"]["tiempo_min"]  == pytest.approx(500 * 1.10)
        assert by_name["Hélice"]["tiempo_min"]          == pytest.approx(500 * 2.50)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Config-driven rates
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteOptionsConfigRates:

    def test_custom_rates_used_over_defaults(self):
        """Custom costo_km / tiempo_km in config must override built-in defaults."""
        config = {
            **DEFAULT_CONFIG,
            "aeronaves": {
                "Avión Comercial": {"costo_km": 0.50, "tiempo_km": 1.00},
            },
        }
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        g.add_edge(_route("A", "B", 100.0, ["Avión Comercial"]))
        svc = AdvancedPlannerService(g, config)
        result = svc.obtener_opciones_ruta("A", "B")
        opt = result["opciones"][0]
        assert opt["costo_usd"]  == pytest.approx(100 * 0.50)
        assert opt["tiempo_min"] == pytest.approx(100 * 1.00)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Subsidised route → zero cost
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteOptionsSubsidized:

    def test_subsidised_route_all_options_zero_cost(self):
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        g.add_edge(_route("A", "B", 300.0,
                          ["Avión Comercial", "Avión Regional"],
                          costo_base=0.0))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        result = svc.obtener_opciones_ruta("A", "B")
        for opt in result["opciones"]:
            assert opt["costo_usd"]  == pytest.approx(0.0)
            assert opt["subsidiada"] is True

    def test_subsidised_flag_true(self):
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        g.add_edge(_route("A", "B", 300.0, ["Avión Comercial"], costo_base=0.0))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        result = svc.obtener_opciones_ruta("A", "B")
        assert result["opciones"][0]["subsidiada"] is True

    def test_non_subsidised_flag_false(self):
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        g.add_edge(_route("A", "B", 300.0, ["Avión Comercial"], costo_base=1.0))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        result = svc.obtener_opciones_ruta("A", "B")
        assert result["opciones"][0]["subsidiada"] is False


# ──────────────────────────────────────────────────────────────────────────────
# 5. Blocked route shows bloqueada=True (still returns options)
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteOptionsBlocked:

    def test_blocked_route_flag_true(self):
        g = _graph_multi_aircraft()
        g.block_route("A", "B")
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        result = svc.obtener_opciones_ruta("A", "B")
        assert result["bloqueada"] is True

    def test_blocked_route_still_lists_options(self):
        g = _graph_multi_aircraft()
        g.block_route("A", "B")
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        result = svc.obtener_opciones_ruta("A", "B")
        assert len(result["opciones"]) == 3


# ──────────────────────────────────────────────────────────────────────────────
# 6 & 7. Error cases
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteOptionsErrors:

    def test_unknown_origin_raises_key_error(self):
        g = _graph_multi_aircraft()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        with pytest.raises(KeyError, match="ZZZ"):
            svc.obtener_opciones_ruta("ZZZ", "B")

    def test_unknown_destination_raises_key_error(self):
        g = _graph_multi_aircraft()
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        with pytest.raises(KeyError, match="ZZZ"):
            svc.obtener_opciones_ruta("A", "ZZZ")

    def test_no_direct_route_raises_value_error(self):
        """A and B exist but no A→B edge."""
        g = AdjacencyGraph()
        g.add_node(_airport("A"))
        g.add_node(_airport("B"))
        svc = AdvancedPlannerService(g, DEFAULT_CONFIG)
        with pytest.raises(ValueError, match="No direct route"):
            svc.obtener_opciones_ruta("A", "B")


# ──────────────────────────────────────────────────────────────────────────────
# 9. Integration against the real network
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteOptionsRealNetwork:

    @pytest.fixture
    def svc(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "network.json"
        )
        graph, config = JSONLoader().load(path)
        return AdvancedPlannerService(graph, config)

    def test_bog_mde_returns_options(self, svc):
        result = svc.obtener_opciones_ruta("BOG", "MDE")
        assert len(result["opciones"]) >= 1

    def test_real_route_costs_positive(self, svc):
        result = svc.obtener_opciones_ruta("BOG", "MDE")
        for opt in result["opciones"]:
            assert opt["costo_usd"] >= 0.0
            assert opt["tiempo_min"] > 0.0

    def test_real_route_distancia_km_positive(self, svc):
        result = svc.obtener_opciones_ruta("BOG", "MDE")
        assert result["distancia_km"] > 0

    def test_real_subsidised_route_zero_cost(self, svc):
        result = svc.obtener_opciones_ruta("CLO", "GYE")
        for opt in result["opciones"]:
            assert opt["costo_usd"] == pytest.approx(0.0)
            assert opt["subsidiada"] is True

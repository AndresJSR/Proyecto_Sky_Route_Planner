"""
Tests for algorithms.shared — shared utilities (SRP / DRY).

Covers:
  * build_aircraft_registry: None returns all defaults; specific list;
    unknown names silently ignored; empty list returns empty registry;
    returned values are Aircraft instances with correct rates.
  * filter_valid_routes: includes valid routes; excludes routes whose
    aircraft are absent from the registry; excludes blocked routes;
    hub filter (include_secondary=False / True).
  * build_result: correct totals from zero, one, and multiple tramos;
    totals are rounded; original path/tramo lists are not mutated.
"""

import pytest

from algorithms.shared import (
    build_aircraft_registry,
    build_result,
    calculate_route_cost,
    calculate_route_time,
    filter_valid_routes,
    select_best_aircraft,
)
from domain.models.aircraft import Aircraft, DEFAULT_AIRCRAFT
from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_airport(iata: str, es_hub: bool = True) -> Airport:
    return Airport(
        id=iata, nombre=f"Airport {iata}", ciudad="City",
        pais="Country", zona_horaria="America/Bogota",
        es_hub=es_hub, costo_alojamiento=50.0, costo_alimentacion=10.0,
    )


def make_route(
    origen: str,
    destino: str,
    km: float,
    aeronaves: list[str] | None = None,
    costo_base: float = 1.0,
) -> Route:
    return Route(
        origen=origen, destino=destino, distancia_km=km,
        aeronaves=aeronaves or ["Avión Comercial"],
        costo_base=costo_base, estancia_minima=60,
    )


@pytest.fixture
def calculation_route() -> Route:
    return make_route(
        origen="A",
        destino="B",
        km=100.0,
        aeronaves=["Avión Comercial", "Hélice"],
        costo_base=1.0,
    )


@pytest.fixture
def filter_graph() -> AdjacencyGraph:
    """
    Graph used to test filter_valid_routes.

    Nodes: A (hub), B (hub), C (secondary), D (secondary)
    Edges from A:
        A → B  (Avión Comercial, 100 km)   — hub destination
        A → C  (Avión Comercial, 200 km)   — secondary destination
        A → D  (Hélice,          300 km)   — secondary, different aircraft
    """
    g = AdjacencyGraph()
    g.add_node(make_airport("A", es_hub=True))
    g.add_node(make_airport("B", es_hub=True))
    g.add_node(make_airport("C", es_hub=False))
    g.add_node(make_airport("D", es_hub=False))
    g.add_edge(make_route("A", "B", 100.0, aeronaves=["Avión Comercial"]))
    g.add_edge(make_route("A", "C", 200.0, aeronaves=["Avión Comercial"]))
    g.add_edge(make_route("A", "D", 300.0, aeronaves=["Hélice"]))
    return g


# ──────────────────────────────────────────────────────────────────────────────
# build_aircraft_registry
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildAircraftRegistry:

    def test_none_returns_all_defaults(self):
        registry = build_aircraft_registry(None)
        assert set(registry.keys()) == set(DEFAULT_AIRCRAFT.keys())

    def test_none_returns_three_aircraft(self):
        registry = build_aircraft_registry(None)
        assert len(registry) == 3

    def test_specific_single_type(self):
        registry = build_aircraft_registry(["Avión Comercial"])
        assert list(registry.keys()) == ["Avión Comercial"]

    def test_specific_two_types(self):
        registry = build_aircraft_registry(["Avión Comercial", "Hélice"])
        assert set(registry.keys()) == {"Avión Comercial", "Hélice"}

    def test_unknown_names_silently_ignored(self):
        registry = build_aircraft_registry(["Avión Supersónico"])
        assert registry == {}

    def test_mixed_valid_and_unknown(self):
        registry = build_aircraft_registry(["Avión Comercial", "Nave Espacial"])
        assert set(registry.keys()) == {"Avión Comercial"}

    def test_empty_list_returns_empty_dict(self):
        registry = build_aircraft_registry([])
        assert registry == {}

    def test_returns_aircraft_instances(self):
        registry = build_aircraft_registry(None)
        for ac in registry.values():
            assert isinstance(ac, Aircraft)

    def test_comercial_rates_match_defaults(self):
        """Default rates: Avión Comercial → $0.18/km, 0.7 min/km."""
        registry = build_aircraft_registry(["Avión Comercial"])
        ac = registry["Avión Comercial"]
        assert ac.costo_km  == pytest.approx(0.18, rel=1e-9)
        assert ac.tiempo_km == pytest.approx(0.70, rel=1e-9)

    def test_regional_rates_match_defaults(self):
        """Default rates: Avión Regional → $0.25/km, 1.1 min/km."""
        registry = build_aircraft_registry(["Avión Regional"])
        ac = registry["Avión Regional"]
        assert ac.costo_km  == pytest.approx(0.25, rel=1e-9)
        assert ac.tiempo_km == pytest.approx(1.10, rel=1e-9)

    def test_helice_rates_match_defaults(self):
        """Default rates: Hélice → $0.12/km, 2.5 min/km."""
        registry = build_aircraft_registry(["Hélice"])
        ac = registry["Hélice"]
        assert ac.costo_km  == pytest.approx(0.12, rel=1e-9)
        assert ac.tiempo_km == pytest.approx(2.50, rel=1e-9)

    def test_each_call_returns_independent_instances(self):
        """Two calls must return separate Aircraft objects (not shared references)."""
        reg_a = build_aircraft_registry(["Avión Comercial"])
        reg_b = build_aircraft_registry(["Avión Comercial"])
        assert reg_a["Avión Comercial"] is not reg_b["Avión Comercial"]


# ──────────────────────────────────────────────────────────────────────────────
# filter_valid_routes
# ──────────────────────────────────────────────────────────────────────────────

class TestFilterValidRoutes:

    def _all_registry(self):
        return build_aircraft_registry(None)

    def _comercial_registry(self):
        return build_aircraft_registry(["Avión Comercial"])

    def _helice_registry(self):
        return build_aircraft_registry(["Hélice"])

    def test_returns_list(self, filter_graph):
        result = filter_valid_routes(filter_graph, "A", self._all_registry(), True)
        assert isinstance(result, list)

    def test_returns_route_objects(self, filter_graph):
        result = filter_valid_routes(filter_graph, "A", self._all_registry(), True)
        for r in result:
            assert isinstance(r, Route)

    def test_all_registry_include_secondary_returns_all_routes(self, filter_graph):
        """With all aircraft and secondary included, all 3 outgoing routes returned."""
        result = filter_valid_routes(filter_graph, "A", self._all_registry(), True)
        destinations = {r.destino for r in result}
        assert destinations == {"B", "C", "D"}

    def test_comercial_registry_excludes_helice_routes(self, filter_graph):
        """A→D uses Hélice only; must be excluded when registry has only Avión Comercial."""
        result = filter_valid_routes(filter_graph, "A", self._comercial_registry(), True)
        destinations = {r.destino for r in result}
        assert "D" not in destinations
        assert destinations == {"B", "C"}

    def test_helice_registry_excludes_comercial_routes(self, filter_graph):
        """A→B and A→C use Avión Comercial only; excluded when registry has only Hélice."""
        result = filter_valid_routes(filter_graph, "A", self._helice_registry(), True)
        destinations = {r.destino for r in result}
        assert destinations == {"D"}

    def test_hub_filter_false_excludes_secondary(self, filter_graph):
        """include_secondary=False → only hub B returned (C and D are secondary)."""
        result = filter_valid_routes(
            filter_graph, "A", self._all_registry(), include_secondary=False
        )
        destinations = {r.destino for r in result}
        assert destinations == {"B"}

    def test_hub_filter_true_includes_secondary(self, filter_graph):
        """include_secondary=True → all reachable aircraft included regardless of hub status."""
        result = filter_valid_routes(
            filter_graph, "A", self._all_registry(), include_secondary=True
        )
        destinations = {r.destino for r in result}
        assert "C" in destinations
        assert "D" in destinations

    def test_blocked_route_excluded(self, filter_graph):
        """A blocked route must not appear in filter results (get_neighbors excludes it)."""
        filter_graph.block_route("A", "B")
        result = filter_valid_routes(filter_graph, "A", self._all_registry(), True)
        destinations = {r.destino for r in result}
        assert "B" not in destinations

    def test_empty_registry_returns_empty(self, filter_graph):
        """No aircraft in registry → no routes are compatible → empty list."""
        result = filter_valid_routes(filter_graph, "A", {}, True)
        assert result == []

    def test_airport_with_no_outgoing_routes(self):
        """An airport with no outgoing routes must return an empty list."""
        g = AdjacencyGraph()
        g.add_node(make_airport("SOLO", es_hub=True))
        result = filter_valid_routes(g, "SOLO", self._all_registry(), True)
        assert result == []


# ──────────────────────────────────────────────────────────────────────────────
# calculate_route_cost / calculate_route_time / select_best_aircraft
# ──────────────────────────────────────────────────────────────────────────────

class TestRouteHelpers:

    def test_calculate_route_cost_normal(self, calculation_route):
        registry = build_aircraft_registry(["Avión Comercial"])
        aircraft = registry["Avión Comercial"]

        assert calculate_route_cost(calculation_route, aircraft) == pytest.approx(18.0)

    def test_calculate_route_cost_subsidized_is_zero(self, calculation_route):
        subsidized_route = make_route(
            origen="A",
            destino="B",
            km=100.0,
            aeronaves=["Avión Comercial"],
            costo_base=0.0,
        )
        aircraft = build_aircraft_registry(["Avión Comercial"])["Avión Comercial"]

        assert calculate_route_cost(subsidized_route, aircraft) == 0.0

    def test_calculate_route_time(self, calculation_route):
        aircraft = build_aircraft_registry(["Avión Comercial"])["Avión Comercial"]

        assert calculate_route_time(calculation_route, aircraft) == pytest.approx(70.0)

    def test_select_best_aircraft_cost_prefers_cheapest(self, calculation_route):
        registry = build_aircraft_registry(["Avión Comercial", "Hélice"])

        aircraft = select_best_aircraft(calculation_route, registry, "cost")

        assert aircraft is not None
        assert aircraft.nombre == "Hélice"

    def test_select_best_aircraft_time_prefers_fastest(self, calculation_route):
        registry = build_aircraft_registry(["Avión Comercial", "Hélice"])

        aircraft = select_best_aircraft(calculation_route, registry, "time")

        assert aircraft is not None
        assert aircraft.nombre == "Avión Comercial"


# ──────────────────────────────────────────────────────────────────────────────
# build_result
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildResult:

    def _tramo(self, km: float, costo: float, tiempo: float) -> dict:
        return {"distancia_km": km, "costo_usd": costo, "tiempo_min": tiempo}

    def test_origin_only_result(self):
        result = build_result(["BOG"], [])
        assert result["ruta"]   == ["BOG"]
        assert result["tramos"] == []
        assert result["total_distancia_km"] == 0.0
        assert result["total_costo_usd"]    == 0.0
        assert result["total_tiempo_min"]   == 0.0

    def test_required_keys_present(self):
        result = build_result(["A"], [])
        assert {"ruta", "tramos", "total_distancia_km",
                "total_costo_usd", "total_tiempo_min"}.issubset(result.keys())

    def test_single_tramo_totals(self):
        tramos = [self._tramo(km=100.0, costo=18.0, tiempo=70.0)]
        result = build_result(["A", "B"], tramos)
        assert result["total_distancia_km"] == pytest.approx(100.0, rel=1e-9)
        assert result["total_costo_usd"]    == pytest.approx(18.0,  rel=1e-9)
        assert result["total_tiempo_min"]   == pytest.approx(70.0,  rel=1e-9)

    def test_multiple_tramos_totals(self):
        tramos = [
            self._tramo(100.0, 18.0, 70.0),
            self._tramo(200.0, 36.0, 140.0),
            self._tramo(300.0, 54.0, 210.0),
        ]
        result = build_result(["A", "B", "C", "D"], tramos)
        assert result["total_distancia_km"] == pytest.approx(600.0,  rel=1e-9)
        assert result["total_costo_usd"]    == pytest.approx(108.0,  rel=1e-9)
        assert result["total_tiempo_min"]   == pytest.approx(420.0,  rel=1e-9)

    def test_ruta_copied_not_mutated(self):
        """Mutating the original path list must not affect the stored result."""
        path = ["A", "B"]
        result = build_result(path, [])
        path.append("C")
        assert result["ruta"] == ["A", "B"]

    def test_tramos_copied_not_mutated(self):
        """Mutating the original tramos list must not affect the stored result."""
        tramo = self._tramo(100.0, 18.0, 70.0)
        tramos = [tramo]
        result = build_result(["A", "B"], tramos)
        tramos.clear()
        assert len(result["tramos"]) == 1

    def test_totals_are_rounded_to_two_decimals(self):
        """build_result must round totals to 2 decimal places."""
        tramos = [self._tramo(km=1.0 / 3, costo=1.0 / 3, tiempo=1.0 / 3)]
        result = build_result(["A", "B"], tramos)
        # 1/3 ≈ 0.333... → rounded to 0.33
        assert result["total_distancia_km"] == round(1.0 / 3, 2)
        assert result["total_costo_usd"]    == round(1.0 / 3, 2)
        assert result["total_tiempo_min"]   == round(1.0 / 3, 2)

    def test_ruta_preserved_in_result(self):
        ruta = ["BOG", "MDE", "CTG"]
        result = build_result(ruta, [self._tramo(100, 18, 70), self._tramo(200, 36, 140)])
        assert result["ruta"] == ["BOG", "MDE", "CTG"]

    def test_zero_distance_tramos(self):
        tramos = [self._tramo(0.0, 0.0, 0.0), self._tramo(0.0, 0.0, 0.0)]
        result = build_result(["A", "B", "C"], tramos)
        assert result["total_distancia_km"] == 0.0
        assert result["total_costo_usd"]    == 0.0
        assert result["total_tiempo_min"]   == 0.0

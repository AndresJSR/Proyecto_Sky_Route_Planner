"""
Tests for Backtracking algorithms — max_destinos_presupuesto and max_destinos_tiempo.

Requirements covered:
  - R3 (Persona 2): Find the itinerary that maximises visited destinations
    without exceeding a budget constraint (max_destinos_presupuesto).
  - R4 (Persona 2): Find the itinerary that maximises visited destinations
    without exceeding a time constraint (max_destinos_tiempo).

Covers:
  * Correct result structure (keys, types, totals).
  * Origin-only result when the constraint is zero or too tight.
  * Correct expansion as budget / time grows.
  * Constraint is never exceeded in any result.
  * Subsidised routes cost $0 and are traversable with $0 budget.
  * incluir_secundarios=False restricts to hub destinations only.
  * tipos_transporte filter excludes incompatible routes.
  * Blocked routes are never used.
  * Result has no cycles (each airport appears at most once).
  * Tramos are contiguous (tramo[i].destino == tramo[i+1].origen).
  * ruta list is consistent with tramos.
  * Integration tests against the real network.
"""

import os
import pytest

from algorithms.backtracking import (
    max_destinos_presupuesto,
    max_destinos_tiempo,
    max_destinos_presupuesto_y_tiempo,
)
from domain.models.aircraft import Aircraft, DEFAULT_AIRCRAFT
from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from infrastructure.json_loader import JSONLoader


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_KEYS = {
    "ruta",
    "tramos",
    "cantidad_destinos",
    "total_distancia_km",
    "total_costo_usd",
    "total_tiempo_min",
}
TRAMO_KEYS    = {"origen", "destino", "distancia_km", "aeronave", "costo_usd", "tiempo_min"}


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
    """costo_base=1.0 → not subsidised; costo_base=0.0 → subsidised."""
    return Route(
        origen=origen, destino=destino, distancia_km=km,
        aeronaves=aeronaves or ["Avión Comercial"],
        costo_base=costo_base, estancia_minima=60,
    )


@pytest.fixture
def tie_graph() -> AdjacencyGraph:
    """
    Graph with two equally long itineraries (two destinations each):
        A → B → D  (more expensive / slower)
        A → C → D  (cheaper / faster)
    """
    g = AdjacencyGraph()
    for iata in ("A", "B", "C", "D"):
        g.add_node(make_airport(iata, es_hub=True))
    g.add_edge(make_route("A", "B", 100.0))
    g.add_edge(make_route("B", "D", 100.0))
    g.add_edge(make_route("A", "C", 50.0))
    g.add_edge(make_route("C", "D", 100.0))
    return g


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def chain_graph() -> AdjacencyGraph:
    """
    Linear chain of 4 hub airports (all hubs, no hub filter needed):
        A ──100 km──► B ──100 km──► C ──100 km──► D

    All routes: Avión Comercial ($0.18/km, 0.7 min/km)
    Per-leg cost: $18.00  |  Per-leg time: 70.00 min  |  Per-leg dist: 100 km
    """
    g = AdjacencyGraph()
    for iata in ("A", "B", "C", "D"):
        g.add_node(make_airport(iata, es_hub=True))
    g.add_edge(make_route("A", "B", 100.0))
    g.add_edge(make_route("B", "C", 100.0))
    g.add_edge(make_route("C", "D", 100.0))
    return g


@pytest.fixture
def hub_secondary_graph() -> AdjacencyGraph:
    """
    Origin HUB_A with two destinations: HUB_B (hub) and SEC_C (secondary).
        HUB_A ──100 km──► HUB_B
        HUB_A ──100 km──► SEC_C
    Both use Avión Comercial.  Useful for testing incluir_secundarios flag.
    """
    g = AdjacencyGraph()
    g.add_node(make_airport("HUB_A", es_hub=True))
    g.add_node(make_airport("HUB_B", es_hub=True))
    g.add_node(make_airport("SEC_C", es_hub=False))
    g.add_edge(make_route("HUB_A", "HUB_B", 100.0))
    g.add_edge(make_route("HUB_A", "SEC_C", 100.0))
    return g


@pytest.fixture
def subsidized_graph() -> AdjacencyGraph:
    """
    Two airports connected by a subsidised route (costo_base=0.0 → cost $0).
        X ──500 km──► Y  (subsidised)
    """
    g = AdjacencyGraph()
    for iata in ("X", "Y"):
        g.add_node(make_airport(iata, es_hub=True))
    g.add_edge(make_route("X", "Y", 500.0, costo_base=0.0))
    return g


@pytest.fixture
def multi_aircraft_graph() -> AdjacencyGraph:
    """
    Single route P→Q with both Avión Comercial (0.7 min/km) and Hélice (2.5 min/km).
    Used to verify that the fastest aircraft is chosen for time optimisation.
    """
    g = AdjacencyGraph()
    for iata in ("P", "Q"):
        g.add_node(make_airport(iata, es_hub=True))
    g.add_edge(make_route("P", "Q", 1000.0, aeronaves=["Hélice", "Avión Comercial"]))
    return g


@pytest.fixture
def real_graph():
    """Full network loaded from data/network.json."""
    loader = JSONLoader()
    graph, config = loader.load(
        os.path.join(os.path.dirname(__file__), "..", "data", "network.json")
    )
    return graph, config


# ──────────────────────────────────────────────────────────────────────────────
# Shared structural helpers used by multiple test classes
# ──────────────────────────────────────────────────────────────────────────────

def assert_valid_structure(result: dict) -> None:
    """Assert that *result* has all required keys with correct types."""
    assert isinstance(result, dict)
    assert REQUIRED_KEYS.issubset(result.keys())
    assert isinstance(result["ruta"],   list)
    assert isinstance(result["tramos"], list)
    assert isinstance(result["total_distancia_km"], (int, float))
    assert isinstance(result["total_costo_usd"],    (int, float))
    assert isinstance(result["total_tiempo_min"],   (int, float))


def assert_tramos_valid(result: dict) -> None:
    """Assert tramo list integrity: keys, contiguity and consistency with ruta."""
    tramos = result["tramos"]
    ruta   = result["ruta"]

    for tramo in tramos:
        assert TRAMO_KEYS.issubset(tramo.keys()), f"Missing keys in tramo: {tramo}"

    # Contiguous: tramo[i].destino == tramo[i+1].origen
    for i in range(len(tramos) - 1):
        assert tramos[i]["destino"] == tramos[i + 1]["origen"], (
            f"Tramo gap at index {i}: {tramos[i]['destino']} ≠ {tramos[i+1]['origen']}"
        )

    # ruta is consistent with tramos
    for i, tramo in enumerate(tramos):
        assert tramo["origen"]  == ruta[i],     f"Tramo {i} origen mismatch"
        assert tramo["destino"] == ruta[i + 1], f"Tramo {i} destino mismatch"


def assert_no_cycles(result: dict) -> None:
    """Each airport must appear at most once in the ruta."""
    ruta = result["ruta"]
    assert len(ruta) == len(set(ruta)), f"Cycle detected in ruta: {ruta}"


# ──────────────────────────────────────────────────────────────────────────────
# max_destinos_presupuesto
# ──────────────────────────────────────────────────────────────────────────────

class TestMaxDestinosPresupuesto:

    # --- Basic structure ---

    def test_returns_dict(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 100.0)
        assert isinstance(result, dict)

    def test_result_keys_present(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 100.0)
        assert REQUIRED_KEYS.issubset(result.keys())

    def test_origin_in_ruta(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 100.0)
        assert result["ruta"][0] == "A"

    # --- Constraint boundary: origin-only ---

    def test_origin_only_when_budget_zero_no_subsidized(self, chain_graph):
        """Budget $0 with no subsidised routes → origin-only result."""
        result = max_destinos_presupuesto(chain_graph, "A", 0.0)
        assert result["ruta"] == ["A"]
        assert result["tramos"] == []
        assert result["total_costo_usd"] == 0.0

    def test_origin_only_when_budget_insufficient(self, chain_graph):
        """Budget $17 < $18 first leg → origin only."""
        result = max_destinos_presupuesto(chain_graph, "A", 17.99)
        assert result["ruta"] == ["A"]

    # --- Correct expansion ---

    def test_visits_one_destination_exact_budget(self, chain_graph):
        """Budget exactly $18 covers only A→B."""
        result = max_destinos_presupuesto(chain_graph, "A", 18.0)
        assert len(result["ruta"]) == 2
        assert result["ruta"] == ["A", "B"]

    def test_visits_two_destinations(self, chain_graph):
        """Budget $36 covers A→B→C."""
        result = max_destinos_presupuesto(chain_graph, "A", 36.0)
        assert result["ruta"] == ["A", "B", "C"]

    def test_visits_all_destinations(self, chain_graph):
        """Budget $54 covers full chain A→B→C→D."""
        result = max_destinos_presupuesto(chain_graph, "A", 54.0)
        assert result["ruta"] == ["A", "B", "C", "D"]

    # --- Constraint invariant ---

    def test_total_cost_does_not_exceed_budget(self, chain_graph):
        """The total cost of any result must never exceed the budget."""
        for budget in (0.0, 18.0, 35.0, 36.0, 53.9, 54.0, 1000.0):
            result = max_destinos_presupuesto(chain_graph, "A", budget)
            assert result["total_costo_usd"] <= budget + 1e-9, (
                f"budget={budget}, got cost={result['total_costo_usd']}"
            )

    def test_total_cost_matches_sum_of_tramos(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 54.0)
        expected = round(sum(t["costo_usd"] for t in result["tramos"]), 2)
        assert result["total_costo_usd"] == pytest.approx(expected, rel=1e-6)

    def test_total_distance_matches_sum_of_tramos(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 54.0)
        expected = round(sum(t["distancia_km"] for t in result["tramos"]), 2)
        assert result["total_distancia_km"] == pytest.approx(expected, rel=1e-6)

    def test_total_time_matches_sum_of_tramos(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 54.0)
        expected = round(sum(t["tiempo_min"] for t in result["tramos"]), 2)
        assert result["total_tiempo_min"] == pytest.approx(expected, rel=1e-6)

    # --- Tramo structure & integrity ---

    def test_tramo_keys_present(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 54.0)
        for tramo in result["tramos"]:
            assert TRAMO_KEYS.issubset(tramo.keys())

    def test_tramos_connect_contiguously(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 54.0)
        assert_tramos_valid(result)

    def test_ruta_matches_tramos(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 54.0)
        ruta   = result["ruta"]
        tramos = result["tramos"]
        assert len(tramos) == len(ruta) - 1
        for i, tramo in enumerate(tramos):
            assert tramo["origen"]  == ruta[i]
            assert tramo["destino"] == ruta[i + 1]

    def test_no_cycles_in_ruta(self, chain_graph):
        result = max_destinos_presupuesto(chain_graph, "A", 1000.0)
        assert_no_cycles(result)

    # --- Subsidised routes ---

    def test_subsidised_route_zero_cost(self, subsidized_graph):
        """Subsidised route must report costo_usd = 0.0 in the tramo."""
        result = max_destinos_presupuesto(subsidized_graph, "X", 0.0)
        # $0 budget but route is free → should visit Y
        assert result["ruta"] == ["X", "Y"]
        assert result["tramos"][0]["costo_usd"] == 0.0
        assert result["total_costo_usd"] == 0.0

    def test_subsidised_route_traversable_with_zero_budget(self, subsidized_graph):
        """A subsidised route must be traversable even when budget = $0."""
        result = max_destinos_presupuesto(subsidized_graph, "X", 0.0)
        assert "Y" in result["ruta"]

    # --- Hub / secondary filter ---

    def test_only_hubs_when_incluir_secundarios_false(self, hub_secondary_graph):
        """With incluir_secundarios=False, secondary airport SEC_C must not appear."""
        result = max_destinos_presupuesto(
            hub_secondary_graph, "HUB_A", 100.0, incluir_secundarios=False
        )
        assert "SEC_C" not in result["ruta"]

    def test_secondary_included_by_default(self, hub_secondary_graph):
        """With default incluir_secundarios=True, SEC_C must be reachable."""
        result = max_destinos_presupuesto(
            hub_secondary_graph, "HUB_A", 100.0, incluir_secundarios=True
        )
        # With $100 both HUB_B and SEC_C cost $18 → one of them is visited
        assert len(result["ruta"]) >= 2

    # --- Aircraft type filter ---

    def test_tipos_transporte_filters_incompatible_routes(self):
        """A route with only Hélice must be ignored when tipos=['Avión Comercial']."""
        g = AdjacencyGraph()
        for iata in ("S", "T"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("S", "T", 100.0, aeronaves=["Hélice"]))
        result = max_destinos_presupuesto(
            g, "S", 1000.0, tipos_transporte=["Avión Comercial"]
        )
        assert result["ruta"] == ["S"]  # route not usable → origin only

    def test_tipos_transporte_allows_matching_routes(self):
        """Only aircraft in tipos_transporte are used."""
        g = AdjacencyGraph()
        for iata in ("S", "T"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("S", "T", 100.0, aeronaves=["Avión Comercial"]))
        result = max_destinos_presupuesto(
            g, "S", 1000.0, tipos_transporte=["Avión Comercial"]
        )
        assert "T" in result["ruta"]

    # --- Route blocking ---

    def test_blocked_route_not_used(self, chain_graph):
        """A blocked route must never appear in the result."""
        chain_graph.block_route("A", "B")
        result = max_destinos_presupuesto(chain_graph, "A", 1000.0)
        assert result["ruta"] == ["A"]  # B is the only neighbour of A, now blocked

    def test_blocked_intermediate_route_limits_chain(self, chain_graph):
        """Blocking B→C means the result can visit A, B but not C or D."""
        chain_graph.block_route("B", "C")
        result = max_destinos_presupuesto(chain_graph, "A", 1000.0)
        assert "C" not in result["ruta"]
        assert "D" not in result["ruta"]
        assert "B" in result["ruta"]

    def test_tie_prefers_lower_cost(self, tie_graph):
        result = max_destinos_presupuesto(tie_graph, "A", 1000.0)

        assert result["ruta"] == ["A", "C", "D"]
        assert result["total_costo_usd"] < 40.0

    # --- More budget → more or equal destinations ---

    def test_more_budget_more_or_equal_destinations(self, chain_graph):
        result_small = max_destinos_presupuesto(chain_graph, "A", 18.0)
        result_large = max_destinos_presupuesto(chain_graph, "A", 54.0)
        assert len(result_large["ruta"]) >= len(result_small["ruta"])

    # --- Integration: real network ---

    def test_real_network_returns_valid_structure(self, real_graph):
        graph, _ = real_graph
        result = max_destinos_presupuesto(graph, "BOG", 500.0)
        assert_valid_structure(result)
        assert_tramos_valid(result)
        assert_no_cycles(result)

    def test_real_network_respects_budget(self, real_graph):
        """Total cost must never exceed the given budget."""
        graph, _ = real_graph
        for budget in (50.0, 200.0, 500.0, 1000.0):
            result = max_destinos_presupuesto(graph, "BOG", budget)
            assert result["total_costo_usd"] <= budget + 1e-6, (
                f"Budget {budget} violated: got {result['total_costo_usd']}"
            )

    def test_real_network_more_budget_more_destinations(self, real_graph):
        """Higher budget must yield at least as many destinations."""
        graph, _ = real_graph
        r_small = max_destinos_presupuesto(graph, "BOG",  100.0)
        r_large = max_destinos_presupuesto(graph, "BOG",  500.0)
        assert len(r_large["ruta"]) >= len(r_small["ruta"])

    def test_real_network_zero_budget_origin_only(self, real_graph):
        """Budget $0 with no subsidised starting leg → origin only."""
        graph, _ = real_graph
        result = max_destinos_presupuesto(graph, "BOG", 0.0)
        assert result["ruta"] == ["BOG"]

    def test_real_network_hubs_only_filter(self, real_graph):
        """With incluir_secundarios=False, only hub airports appear in ruta."""
        graph, _ = real_graph
        result = max_destinos_presupuesto(
            graph, "BOG", 800.0, incluir_secundarios=False
        )
        for iata in result["ruta"]:
            assert graph.get_node(iata).es_hub, f"{iata} is not a hub"

    def test_real_network_visits_multiple_destinations(self, real_graph):
        """With $500 budget, BOG should be able to visit at least 3 destinations."""
        graph, _ = real_graph
        result = max_destinos_presupuesto(graph, "BOG", 500.0)
        assert len(result["ruta"]) >= 3

    def test_real_network_tramos_contiguous(self, real_graph):
        graph, _ = real_graph
        result = max_destinos_presupuesto(graph, "BOG", 500.0)
        assert_tramos_valid(result)


# ──────────────────────────────────────────────────────────────────────────────
# max_destinos_tiempo
# ──────────────────────────────────────────────────────────────────────────────

class TestMaxDestinosTiempo:

    # --- Basic structure ---

    def test_returns_dict(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 300.0)
        assert isinstance(result, dict)

    def test_result_keys_present(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 300.0)
        assert REQUIRED_KEYS.issubset(result.keys())

    def test_origin_in_ruta(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 300.0)
        assert result["ruta"][0] == "A"

    # --- Constraint boundary: origin-only ---

    def test_origin_only_when_time_zero(self, chain_graph):
        """Time=0 → no leg can be taken → origin-only result."""
        result = max_destinos_tiempo(chain_graph, "A", 0.0)
        assert result["ruta"] == ["A"]
        assert result["tramos"] == []
        assert result["total_tiempo_min"] == 0.0

    def test_origin_only_when_time_insufficient(self, chain_graph):
        """Time 69 min < 70 min first leg → origin only."""
        result = max_destinos_tiempo(chain_graph, "A", 69.99)
        assert result["ruta"] == ["A"]

    # --- Correct expansion ---

    def test_visits_one_destination_exact_time(self, chain_graph):
        """Time exactly 70 min covers only A→B."""
        result = max_destinos_tiempo(chain_graph, "A", 70.0)
        assert result["ruta"] == ["A", "B"]

    def test_visits_two_destinations(self, chain_graph):
        """Time 140 min covers A→B→C."""
        result = max_destinos_tiempo(chain_graph, "A", 140.0)
        assert result["ruta"] == ["A", "B", "C"]

    def test_visits_all_destinations(self, chain_graph):
        """Time 210 min covers full chain A→B→C→D."""
        result = max_destinos_tiempo(chain_graph, "A", 210.0)
        assert result["ruta"] == ["A", "B", "C", "D"]

    # --- Constraint invariant ---

    def test_total_time_does_not_exceed_limit(self, chain_graph):
        """Total time of any result must never exceed the time limit."""
        for limit in (0.0, 70.0, 139.0, 140.0, 209.9, 210.0, 9999.0):
            result = max_destinos_tiempo(chain_graph, "A", limit)
            assert result["total_tiempo_min"] <= limit + 1e-9, (
                f"limit={limit}, got time={result['total_tiempo_min']}"
            )

    def test_total_time_matches_sum_of_tramos(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 210.0)
        expected = round(sum(t["tiempo_min"] for t in result["tramos"]), 2)
        assert result["total_tiempo_min"] == pytest.approx(expected, rel=1e-6)

    def test_total_cost_matches_sum_of_tramos(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 210.0)
        expected = round(sum(t["costo_usd"] for t in result["tramos"]), 2)
        assert result["total_costo_usd"] == pytest.approx(expected, rel=1e-6)

    # --- Aircraft selection: fastest wins ---

    def test_chooses_fastest_aircraft(self, multi_aircraft_graph):
        """
        Route P→Q has Hélice (2.5 min/km) and Avión Comercial (0.7 min/km).
        max_destinos_tiempo must choose Avión Comercial (faster).
        Expected time: 1000 km * 0.7 = 700 min.
        """
        result = max_destinos_tiempo(multi_aircraft_graph, "P", 3000.0)
        assert "Q" in result["ruta"]
        assert result["tramos"][0]["aeronave"] == "Avión Comercial"
        assert result["total_tiempo_min"] == pytest.approx(700.0, rel=1e-3)

    def test_fastest_aircraft_minimises_total_time(self, multi_aircraft_graph):
        """
        The Hélice would need 2500 min for the same leg.
        The result time must be 700 min (Avión Comercial), not 2500.
        """
        result = max_destinos_tiempo(multi_aircraft_graph, "P", 3000.0)
        assert result["total_tiempo_min"] < 2500.0

    def test_tie_prefers_lower_time(self, tie_graph):
        result = max_destinos_tiempo(tie_graph, "A", 1000.0)

        assert result["ruta"] == ["A", "C", "D"]
        assert result["total_tiempo_min"] < 200.0

    # --- Tramo structure & integrity ---

    def test_tramo_keys_present(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 210.0)
        for tramo in result["tramos"]:
            assert TRAMO_KEYS.issubset(tramo.keys())

    def test_tramos_connect_contiguously(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 210.0)
        assert_tramos_valid(result)

    def test_ruta_matches_tramos(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 210.0)
        ruta   = result["ruta"]
        tramos = result["tramos"]
        assert len(tramos) == len(ruta) - 1
        for i, tramo in enumerate(tramos):
            assert tramo["origen"]  == ruta[i]
            assert tramo["destino"] == ruta[i + 1]

    def test_no_cycles_in_ruta(self, chain_graph):
        result = max_destinos_tiempo(chain_graph, "A", 9999.0)
        assert_no_cycles(result)

    # --- Hub / secondary filter ---

    def test_only_hubs_when_incluir_secundarios_false(self, hub_secondary_graph):
        result = max_destinos_tiempo(
            hub_secondary_graph, "HUB_A", 300.0, incluir_secundarios=False
        )
        assert "SEC_C" not in result["ruta"]

    def test_secondary_included_by_default(self, hub_secondary_graph):
        result = max_destinos_tiempo(
            hub_secondary_graph, "HUB_A", 300.0, incluir_secundarios=True
        )
        assert len(result["ruta"]) >= 2

    # --- Route blocking ---

    def test_blocked_route_not_used(self, chain_graph):
        chain_graph.block_route("A", "B")
        result = max_destinos_tiempo(chain_graph, "A", 9999.0)
        assert result["ruta"] == ["A"]

    def test_blocked_intermediate_limits_chain(self, chain_graph):
        chain_graph.block_route("B", "C")
        result = max_destinos_tiempo(chain_graph, "A", 9999.0)
        assert "C" not in result["ruta"]
        assert "D" not in result["ruta"]

    # --- Aircraft type filter ---

    def test_tipos_transporte_filters_incompatible_routes(self):
        g = AdjacencyGraph()
        for iata in ("U", "V"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("U", "V", 100.0, aeronaves=["Hélice"]))
        result = max_destinos_tiempo(g, "U", 9999.0, tipos_transporte=["Avión Comercial"])
        assert result["ruta"] == ["U"]  # Hélice route is not usable

    # --- More time → more or equal destinations ---

    def test_more_time_more_or_equal_destinations(self, chain_graph):
        result_small = max_destinos_tiempo(chain_graph, "A", 70.0)
        result_large = max_destinos_tiempo(chain_graph, "A", 210.0)
        assert len(result_large["ruta"]) >= len(result_small["ruta"])

    # --- Integration: real network ---

    def test_real_network_returns_valid_structure(self, real_graph):
        graph, _ = real_graph
        result = max_destinos_tiempo(graph, "BOG", 2000.0)
        assert_valid_structure(result)
        assert_tramos_valid(result)
        assert_no_cycles(result)

    def test_real_network_respects_time_limit(self, real_graph):
        """Total time must never exceed the given limit."""
        graph, _ = real_graph
        for limit in (300.0, 1000.0, 2000.0, 5000.0):
            result = max_destinos_tiempo(graph, "BOG", limit)
            assert result["total_tiempo_min"] <= limit + 1e-6, (
                f"Limit {limit} violated: got {result['total_tiempo_min']}"
            )

    def test_real_network_more_time_more_destinations(self, real_graph):
        graph, _ = real_graph
        r_small = max_destinos_tiempo(graph, "BOG", 500.0)
        r_large = max_destinos_tiempo(graph, "BOG", 2000.0)
        assert len(r_large["ruta"]) >= len(r_small["ruta"])

    def test_real_network_zero_time_origin_only(self, real_graph):
        graph, _ = real_graph
        result = max_destinos_tiempo(graph, "BOG", 0.0)
        assert result["ruta"] == ["BOG"]

    def test_real_network_hubs_only_filter(self, real_graph):
        graph, _ = real_graph
        result = max_destinos_tiempo(
            graph, "BOG", 2000.0, incluir_secundarios=False
        )
        for iata in result["ruta"]:
            assert graph.get_node(iata).es_hub, f"{iata} is not a hub"

    def test_real_network_visits_multiple_destinations(self, real_graph):
        """With 2000 min, BOG should be able to visit at least 3 destinations."""
        graph, _ = real_graph
        result = max_destinos_tiempo(graph, "BOG", 2000.0)
        assert len(result["ruta"]) >= 3

    def test_real_network_tramos_contiguous(self, real_graph):
        graph, _ = real_graph
        result = max_destinos_tiempo(graph, "BOG", 2000.0)
        assert_tramos_valid(result)


# ──────────────────────────────────────────────────────────────────────────────
# Cross-variant consistency
# ──────────────────────────────────────────────────────────────────────────────

class TestBacktrackingCrossVariant:

    def test_both_return_same_structure(self, chain_graph):
        """Both functions must return dicts with identical key sets."""
        r_pres = max_destinos_presupuesto(chain_graph, "A", 54.0)
        r_time = max_destinos_tiempo(chain_graph, "A", 210.0)
        assert set(r_pres.keys()) == set(r_time.keys()) == REQUIRED_KEYS

    def test_both_origin_only_with_zero_constraint(self, chain_graph):
        r_pres = max_destinos_presupuesto(chain_graph, "A", 0.0)
        r_time = max_destinos_tiempo(chain_graph, "A", 0.0)
        assert r_pres["ruta"] == ["A"]
        assert r_time["ruta"] == ["A"]

    def test_both_visit_all_with_generous_constraint(self, chain_graph):
        """With generous limits, both variants must traverse the full chain."""
        r_pres = max_destinos_presupuesto(chain_graph, "A", 9999.0)
        r_time = max_destinos_tiempo(chain_graph, "A", 9999.0)
        assert r_pres["ruta"] == ["A", "B", "C", "D"]
        assert r_time["ruta"] == ["A", "B", "C", "D"]

    def test_real_network_both_no_cycles(self, real_graph):
        graph, _ = real_graph
        r_pres = max_destinos_presupuesto(graph, "BOG", 500.0)
        r_time = max_destinos_tiempo(graph, "BOG", 2000.0)
        assert_no_cycles(r_pres)
        assert_no_cycles(r_time)

    def test_real_network_both_tramos_contiguous(self, real_graph):
        graph, _ = real_graph
        r_pres = max_destinos_presupuesto(graph, "BOG", 500.0)
        r_time = max_destinos_tiempo(graph, "BOG", 2000.0)
        assert_tramos_valid(r_pres)
        assert_tramos_valid(r_time)

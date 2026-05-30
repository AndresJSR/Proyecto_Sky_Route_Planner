"""
Tests for Dijkstra algorithms — three variants (Persona 2, R2).

Covers: correctness of shortest path by cost, time and distance;
        directed graph (no implicit reverse); blocked routes;
        subsidised routes; no-path case; custom aircraft rates;
        KeyError on unknown airports.
"""

import pytest

from algorithms.dijkstra import dijkstra_costo, dijkstra_tiempo, dijkstra_distancia
from domain.models.aircraft import Aircraft, DEFAULT_AIRCRAFT
from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from infrastructure.json_loader import JSONLoader
import os


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def make_airport(iata: str, es_hub: bool = False) -> Airport:
    return Airport(
        id=iata, nombre=f"Airport {iata}", ciudad="City",
        pais="Country", zona_horaria="America/Bogota",
        es_hub=es_hub, costo_alojamiento=50.0, costo_alimentacion=10.0,
    )


def make_route(origen: str, destino: str, km: float,
               aeronaves: list[str] | None = None,
               costo_base: float = 1.0) -> Route:
    return Route(
        origen=origen, destino=destino, distancia_km=km,
        aeronaves=aeronaves or ["Avión Comercial"],
        costo_base=costo_base, estancia_minima=60,
    )


def default_registry() -> dict[str, Aircraft]:
    return {n: Aircraft.from_defaults(n) for n in DEFAULT_AIRCRAFT}


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def linear_graph() -> AdjacencyGraph:
    """
    Simple linear graph: A → B → C (directed, no reverse)
    Distances: A→B = 100 km, B→C = 200 km
    """
    g = AdjacencyGraph()
    for iata in ("A", "B", "C"):
        g.add_node(make_airport(iata))
    g.add_edge(make_route("A", "B", 100.0))
    g.add_edge(make_route("B", "C", 200.0))
    return g


@pytest.fixture
def diamond_graph() -> AdjacencyGraph:
    """
    Diamond-shaped graph to verify algorithm picks the best path:

        A ──(500 km)──► B ──(500 km)──► D
        └──(200 km)──► C ──(200 km)──┘

    By distance: A→C→D = 400 km  (optimal)
    By cost with Avión Comercial ($0.18/km):
        A→B→D = 1000 * 0.18 = $180
        A→C→D =  400 * 0.18 = $72  (optimal)
    """
    g = AdjacencyGraph()
    for iata in ("A", "B", "C", "D"):
        g.add_node(make_airport(iata))
    g.add_edge(make_route("A", "B", 500.0))
    g.add_edge(make_route("A", "C", 200.0))
    g.add_edge(make_route("B", "D", 500.0))
    g.add_edge(make_route("C", "D", 200.0))
    return g


@pytest.fixture
def real_graph():
    """Full network loaded from data/network.json."""
    loader = JSONLoader()
    graph, config = loader.load(
        os.path.join(os.path.dirname(__file__), "..", "data", "network.json")
    )
    return graph, config


# ──────────────────────────────────────────────
# dijkstra_costo
# ──────────────────────────────────────────────

class TestDijkstraCosto:
    def test_returns_dict_on_success(self, linear_graph):
        result = dijkstra_costo(linear_graph, "A", "C")
        assert result is not None
        assert isinstance(result, dict)

    def test_result_keys_present(self, linear_graph):
        result = dijkstra_costo(linear_graph, "A", "C")
        for key in ("ruta", "tramos", "total_distancia_km", "total_costo_usd", "total_tiempo_min"):
            assert key in result

    def test_correct_path_linear(self, linear_graph):
        result = dijkstra_costo(linear_graph, "A", "C")
        assert result["ruta"] == ["A", "B", "C"]

    def test_single_hop(self, linear_graph):
        result = dijkstra_costo(linear_graph, "A", "B")
        assert result["ruta"] == ["A", "B"]
        assert len(result["tramos"]) == 1

    def test_origin_equals_destination(self, linear_graph):
        result = dijkstra_costo(linear_graph, "A", "A")
        assert result["ruta"] == ["A"]
        assert result["total_costo_usd"] == 0.0

    def test_chooses_cheaper_path_in_diamond(self, diamond_graph):
        result = dijkstra_costo(diamond_graph, "A", "D")
        assert result["ruta"] == ["A", "C", "D"]

    def test_total_cost_correct(self, linear_graph):
        result = dijkstra_costo(linear_graph, "A", "C")
        # A→B: 100 * 0.18 = 18, B→C: 200 * 0.18 = 36 → total = 54
        assert result["total_costo_usd"] == pytest.approx(54.0, rel=1e-3)

    def test_subsidised_route_costs_zero(self):
        g = AdjacencyGraph()
        for iata in ("X", "Y"):
            g.add_node(make_airport(iata))
        g.add_edge(make_route("X", "Y", 1000.0, costo_base=0.0))
        result = dijkstra_costo(g, "X", "Y")
        assert result["total_costo_usd"] == 0.0

    def test_no_path_returns_none(self, linear_graph):
        # C has no outgoing edges → C→A is unreachable
        result = dijkstra_costo(linear_graph, "C", "A")
        assert result is None

    def test_blocked_route_not_used(self, linear_graph):
        linear_graph.block_route("A", "B")
        result = dijkstra_costo(linear_graph, "A", "C")
        assert result is None

    def test_respects_allowed_transport_types(self):
        g = AdjacencyGraph()
        for iata in ("X", "Y"):
            g.add_node(make_airport(iata))
        g.add_edge(make_route("X", "Y", 100.0, aeronaves=["Hélice"]))

        result = dijkstra_costo(g, "X", "Y", tipos_transporte=["Avión Comercial"])

        assert result is None

    def test_unknown_origin_raises(self, linear_graph):
        with pytest.raises(KeyError):
            dijkstra_costo(linear_graph, "ZZZ", "C")

    def test_unknown_destination_raises(self, linear_graph):
        with pytest.raises(KeyError):
            dijkstra_costo(linear_graph, "A", "ZZZ")

    def test_prefers_cheapest_aircraft(self):
        """When multiple aircraft on same route, cheapest is chosen."""
        g = AdjacencyGraph()
        for iata in ("P", "Q"):
            g.add_node(make_airport(iata))
        # Both Avión Comercial ($0.18) and Hélice ($0.12) available
        g.add_edge(make_route("P", "Q", 1000.0, aeronaves=["Avión Comercial", "Hélice"]))
        result = dijkstra_costo(g, "P", "Q")
        assert result["tramos"][0]["aeronave"] == "Hélice"
        assert result["total_costo_usd"] == pytest.approx(120.0, rel=1e-3)

    def test_real_network_bog_to_scl(self, real_graph):
        graph, _ = real_graph
        result = dijkstra_costo(graph, "BOG", "SCL")
        assert result is not None
        assert result["ruta"][0] == "BOG"
        assert result["ruta"][-1] == "SCL"
        assert result["total_costo_usd"] > 0


# ──────────────────────────────────────────────
# dijkstra_tiempo
# ──────────────────────────────────────────────

class TestDijkstraTiempo:
    def test_returns_dict_on_success(self, linear_graph):
        result = dijkstra_tiempo(linear_graph, "A", "C")
        assert result is not None

    def test_correct_path_linear(self, linear_graph):
        result = dijkstra_tiempo(linear_graph, "A", "C")
        assert result["ruta"] == ["A", "B", "C"]

    def test_total_time_correct(self, linear_graph):
        # Avión Comercial: 0.7 min/km → 300 km * 0.7 = 210 min
        result = dijkstra_tiempo(linear_graph, "A", "C")
        assert result["total_tiempo_min"] == pytest.approx(210.0, rel=1e-3)

    def test_prefers_fastest_aircraft(self):
        """When multiple aircraft available, fastest (lowest tiempo_km) is chosen."""
        g = AdjacencyGraph()
        for iata in ("P", "Q"):
            g.add_node(make_airport(iata))
        # Avión Comercial: 0.7 min/km, Hélice: 2.5 min/km → Comercial is faster
        g.add_edge(make_route("P", "Q", 1000.0, aeronaves=["Hélice", "Avión Comercial"]))
        result = dijkstra_tiempo(g, "P", "Q")
        assert result["tramos"][0]["aeronave"] == "Avión Comercial"
        assert result["total_tiempo_min"] == pytest.approx(700.0, rel=1e-3)

    def test_chooses_faster_path_in_diamond(self):
        """
        Diamond where the shorter-km path is also faster.
        A→C→D = 400 km * 0.7 = 280 min
        A→B→D = 1000 km * 0.7 = 700 min
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C", "D"):
            g.add_node(make_airport(iata))
        g.add_edge(make_route("A", "B", 500.0))
        g.add_edge(make_route("A", "C", 200.0))
        g.add_edge(make_route("B", "D", 500.0))
        g.add_edge(make_route("C", "D", 200.0))
        result = dijkstra_tiempo(g, "A", "D")
        assert result["ruta"] == ["A", "C", "D"]

    def test_no_path_returns_none(self, linear_graph):
        result = dijkstra_tiempo(linear_graph, "C", "A")
        assert result is None

    def test_blocked_route_not_used(self, linear_graph):
        linear_graph.block_route("A", "B")
        result = dijkstra_tiempo(linear_graph, "A", "C")
        assert result is None

    def test_custom_registry_overrides_rates(self, linear_graph):
        fast = Aircraft(nombre="Avión Comercial", costo_km=0.18, tiempo_km=0.1)
        registry = {"Avión Comercial": fast}
        result = dijkstra_tiempo(linear_graph, "A", "C", aircraft_registry=registry)
        assert result["total_tiempo_min"] == pytest.approx(30.0, rel=1e-3)

    def test_real_network_bog_to_eze(self, real_graph):
        graph, _ = real_graph
        result = dijkstra_tiempo(graph, "BOG", "EZE")
        assert result is not None
        assert result["ruta"][0] == "BOG"
        assert result["ruta"][-1] == "EZE"
        assert result["total_tiempo_min"] > 0


# ──────────────────────────────────────────────
# dijkstra_distancia
# ──────────────────────────────────────────────

class TestDijkstraDistancia:
    def test_returns_dict_on_success(self, linear_graph):
        result = dijkstra_distancia(linear_graph, "A", "C")
        assert result is not None

    def test_correct_path_linear(self, linear_graph):
        result = dijkstra_distancia(linear_graph, "A", "C")
        assert result["ruta"] == ["A", "B", "C"]

    def test_total_distance_correct(self, linear_graph):
        result = dijkstra_distancia(linear_graph, "A", "C")
        assert result["total_distancia_km"] == pytest.approx(300.0, rel=1e-3)

    def test_chooses_shorter_path_in_diamond(self, diamond_graph):
        result = dijkstra_distancia(diamond_graph, "A", "D")
        assert result["ruta"] == ["A", "C", "D"]
        assert result["total_distancia_km"] == pytest.approx(400.0, rel=1e-3)

    def test_no_path_returns_none(self, linear_graph):
        result = dijkstra_distancia(linear_graph, "C", "A")
        assert result is None

    def test_blocked_route_not_used(self, linear_graph):
        linear_graph.block_route("A", "B")
        result = dijkstra_distancia(linear_graph, "A", "C")
        assert result is None

    def test_aircraft_does_not_affect_distance_weight(self):
        """Distance must be the same regardless of which aircraft is on the route."""
        g = AdjacencyGraph()
        for iata in ("P", "Q"):
            g.add_node(make_airport(iata))
        g.add_edge(make_route("P", "Q", 800.0, aeronaves=["Hélice"]))
        result_default = dijkstra_distancia(g, "P", "Q")
        custom = {"Hélice": Aircraft("Hélice", costo_km=99.0, tiempo_km=99.0)}
        result_custom  = dijkstra_distancia(g, "P", "Q", aircraft_registry=custom)
        assert result_default["total_distancia_km"] == result_custom["total_distancia_km"]

    def test_real_network_bog_to_gru(self, real_graph):
        graph, _ = real_graph
        result = dijkstra_distancia(graph, "BOG", "GRU")
        assert result is not None
        assert result["ruta"][0] == "BOG"
        assert result["ruta"][-1] == "GRU"
        assert result["total_distancia_km"] > 0


# ──────────────────────────────────────────────
# Cross-variant consistency checks
# ──────────────────────────────────────────────

class TestCrossVariant:
    def test_all_three_reach_same_destination(self, real_graph):
        graph, _ = real_graph
        for fn in (dijkstra_costo, dijkstra_tiempo, dijkstra_distancia):
            result = fn(graph, "BOG", "LIM")
            assert result is not None
            assert result["ruta"][-1] == "LIM"

    def test_tramos_connect_contiguously(self, real_graph):
        """Every tramo[i].destino must equal tramo[i+1].origen."""
        graph, _ = real_graph
        result = dijkstra_costo(graph, "BOG", "EZE")
        assert result is not None
        for i in range(len(result["tramos"]) - 1):
            assert result["tramos"][i]["destino"] == result["tramos"][i + 1]["origen"]

    def test_ruta_matches_tramos(self, real_graph):
        """ruta list must be consistent with tramos origins/destinations."""
        graph, _ = real_graph
        result = dijkstra_distancia(graph, "BOG", "SCL")
        assert result is not None
        ruta = result["ruta"]
        for i, tramo in enumerate(result["tramos"]):
            assert tramo["origen"]  == ruta[i]
            assert tramo["destino"] == ruta[i + 1]

    def test_distance_optimal_le_cost_path_distance(self, diamond_graph):
        """
        The distance-optimal path must have total_distancia_km <=
        that of the cost-optimal path (which may differ).
        """
        r_dist = dijkstra_distancia(diamond_graph, "A", "D")
        r_cost = dijkstra_costo(diamond_graph, "A", "D")
        assert r_dist["total_distancia_km"] <= r_cost["total_distancia_km"]

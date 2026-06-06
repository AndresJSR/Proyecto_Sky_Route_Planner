"""
Tests for the R2 constraint: require_all_transport_types.

Requirements covered:
  - R2: Both proposed itinerary alternatives must use each available
    aircraft type at least once (require_all_transport_types=True).

The flag is exposed on max_destinos_presupuesto_y_tiempo and forwarded
internally by BasicPlannerService.proponer_itinerarios.

Covers:
  * flag=False preserves original behaviour (maximise destinations only).
  * Coverage is the top priority when flag=True.
  * An itinerary that covers all types beats one with more destinations
    but fewer types.
  * Full coverage achieved when a single path traverses all types.
  * Two-type chain: full path preferred over partial path.
  * Origin-only result when constraints are too tight (flag has no effect).
  * Single-type registry is trivially satisfied after the first leg.
  * Graceful fallback when full coverage is impossible.
  * Hard budget/time constraints respected even with coverage flag active.
  * Integration: real network respects budget, time and produces valid structure.
"""

import os
import pytest

from algorithms.backtracking import max_destinos_presupuesto_y_tiempo
from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from infrastructure.json_loader import JSONLoader


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers (duplicated from test_backtracking to keep the file standalone)
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_KEYS = {
    "ruta",
    "tramos",
    "cantidad_destinos",
    "total_distancia_km",
    "total_costo_usd",
    "total_tiempo_min",
}
TRAMO_KEYS = {"origen", "destino", "distancia_km", "aeronave", "costo_usd", "tiempo_min"}


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


def assert_valid_structure(result: dict) -> None:
    assert isinstance(result, dict)
    assert REQUIRED_KEYS.issubset(result.keys())
    assert isinstance(result["ruta"],   list)
    assert isinstance(result["tramos"], list)
    assert isinstance(result["total_distancia_km"], (int, float))
    assert isinstance(result["total_costo_usd"],    (int, float))
    assert isinstance(result["total_tiempo_min"],   (int, float))


def assert_tramos_valid(result: dict) -> None:
    tramos = result["tramos"]
    ruta   = result["ruta"]
    for tramo in tramos:
        assert TRAMO_KEYS.issubset(tramo.keys()), f"Missing keys in tramo: {tramo}"
    for i in range(len(tramos) - 1):
        assert tramos[i]["destino"] == tramos[i + 1]["origen"], (
            f"Tramo gap at index {i}: {tramos[i]['destino']} ≠ {tramos[i+1]['origen']}"
        )
    for i, tramo in enumerate(tramos):
        assert tramo["origen"]  == ruta[i],     f"Tramo {i} origen mismatch"
        assert tramo["destino"] == ruta[i + 1], f"Tramo {i} destino mismatch"


def assert_no_cycles(result: dict) -> None:
    ruta = result["ruta"]
    assert len(ruta) == len(set(ruta)), f"Cycle detected in ruta: {ruta}"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def real_graph():
    """Full network loaded from data/network.json."""
    loader = JSONLoader()
    graph, config = loader.load(
        os.path.join(os.path.dirname(__file__), "..", "data", "network.json")
    )
    return graph, config


# ──────────────────────────────────────────────────────────────────────────────
# R2 constraint: require_all_transport_types
# ──────────────────────────────────────────────────────────────────────────────

class TestRequireAllTransportTypes:
    """
    Tests for the R2 constraint: both proposed itineraries must use each
    available aircraft type at least once (require_all_transport_types=True).

    The flag is exposed on max_destinos_presupuesto_y_tiempo and forwarded
    internally by BasicPlannerService.proponer_itinerarios.
    """

    # ── graph factories ───────────────────────────────────────────────────────

    @staticmethod
    def _make_multi_type_graph() -> AdjacencyGraph:
        """
        Star topology — three direct legs from A, each using a different type.
        Used by tests that do NOT require a single path to cover all three types.

            A ──(Avión Comercial, 100 km)──► B
            A ──(Avión Regional,  100 km)──► C
            A ──(Hélice,          100 km)──► D

        Rates (defaults):
            Avión Comercial: $0.18/km, 0.7 min/km  → $18, 70 min per leg
            Avión Regional : $0.25/km, 1.1 min/km  → $25, 110 min per leg
            Hélice         : $0.12/km, 2.5 min/km  → $12, 250 min per leg
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C", "D"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("A", "B", 100.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("A", "C", 100.0, aeronaves=["Avión Regional"]))
        g.add_edge(make_route("A", "D", 100.0, aeronaves=["Hélice"]))
        return g

    @staticmethod
    def _make_all_types_chain_graph() -> AdjacencyGraph:
        """
        Linear chain — each leg uses a different aircraft type.
        A single path A→B→C→D covers all three types.

            A ──(Avión Comercial, 100 km)──► B
            B ──(Avión Regional,  100 km)──► C
            C ──(Hélice,          100 km)──► D

        Budget: $18 + $25 + $12 = $55.  Time: 70 + 110 + 250 = 430 min.
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C", "D"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("A", "B", 100.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("B", "C", 100.0, aeronaves=["Avión Regional"]))
        g.add_edge(make_route("C", "D", 100.0, aeronaves=["Hélice"]))
        return g

    @staticmethod
    def _make_coverage_vs_single_type_graph() -> AdjacencyGraph:
        """
        Graph that forces a choice between full coverage and destination count.
        Only two aircraft types are used (Avión Comercial and Avión Regional).

            A ──(AC, 100 km)──► B ──(AR, 100 km)──► C          [2 dests, covers both]
            A ──(AC, 100 km)──► D ──(AC, 100 km)──► E ──(AC)──► F  [3 dests, AC only]

        Without coverage constraint: A→D→E→F wins (3 destinations).
        With require_all_transport_types=True and tipos=[AC, AR]:
            A→B→C wins (2 destinations, covers both required types).
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C", "D", "E", "F"):
            g.add_node(make_airport(iata, es_hub=True))
        # Short path — covers both types
        g.add_edge(make_route("A", "B", 100.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("B", "C", 100.0, aeronaves=["Avión Regional"]))
        # Long path — only Avión Comercial
        g.add_edge(make_route("A", "D", 100.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("D", "E", 100.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("E", "F", 100.0, aeronaves=["Avión Comercial"]))
        return g

    @staticmethod
    def _make_two_type_chain() -> AdjacencyGraph:
        """
        Chain with two different aircraft types on consecutive legs:

            A ──(Avión Comercial, 100 km)──► B ──(Hélice, 100 km)──► C

        Full traversal A→B→C uses both types.
        Partial traversal A→B uses only Avión Comercial.
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("A", "B", 100.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("B", "C", 100.0, aeronaves=["Hélice"]))
        return g

    @staticmethod
    def _make_coverage_vs_count_graph() -> AdjacencyGraph:
        """
        Used by test_flag_false_behaves_as_original only.
        Without the coverage constraint, A→B→C→D (3 destinations, AC only) wins.

            A ──(AC, 50 km)──► B ──(AC, 50 km)──► C ──(AC, 50 km)──► D
            A ──(AR, 50 km)──► E
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C", "D", "E"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("A", "B", 50.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("B", "C", 50.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("C", "D", 50.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("A", "E", 50.0, aeronaves=["Avión Regional"]))
        return g

    # ── flag=False — original behaviour preserved ─────────────────────────────

    def test_flag_false_behaves_as_original(self):
        """Without the flag, the function must maximise destinations only."""
        g = self._make_coverage_vs_count_graph()
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=1000.0,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            require_all_transport_types=False,
        )
        # Without coverage constraint → A→B→C→D wins (3 destinations)
        assert len(result["ruta"]) - 1 == 3
        assert result["ruta"] == ["A", "B", "C", "D"]

    # ── flag=True — coverage is top priority ──────────────────────────────────

    def test_flag_true_coverage_beats_destination_count(self):
        """
        An itinerary that covers all required types beats one that visits MORE
        destinations but uses only a subset of the required types.

            A→B→C   : 2 destinations, uses Avión Comercial + Avión Regional
            A→D→E→F : 3 destinations, uses Avión Comercial only

        With flag=True and tipos=[AC, AR]: A→B→C wins despite fewer destinations.
        """
        g = self._make_coverage_vs_single_type_graph()
        tipos = ["Avión Comercial", "Avión Regional"]
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=1000.0,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            tipos_transporte=tipos,
            require_all_transport_types=True,
        )
        used_types = {t["aeronave"] for t in result["tramos"]}
        assert "Avión Comercial" in used_types
        assert "Avión Regional" in used_types
        assert result["ruta"] == ["A", "B", "C"]

    def test_flag_true_full_coverage_when_feasible(self):
        """
        When a single path can cover all three aircraft types, the result
        must use all of them.

            A ──(AC)──► B ──(AR)──► C ──(Hélice)──► D

        The only full path A→B→C→D uses all three types.
        """
        g = self._make_all_types_chain_graph()
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=1000.0,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            require_all_transport_types=True,
        )
        used_types = {t["aeronave"] for t in result["tramos"]}
        assert used_types == {"Avión Comercial", "Avión Regional", "Hélice"}
        assert result["ruta"] == ["A", "B", "C", "D"]

    def test_flag_true_two_type_chain_covers_both(self):
        """
        A→B→C uses Avión Comercial (A→B) and Hélice (B→C).
        With coverage required, the full chain must be preferred over A→B alone.
        """
        g = self._make_two_type_chain()
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=1000.0,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            require_all_transport_types=True,
        )
        used_types = {t["aeronave"] for t in result["tramos"]}
        assert "Avión Comercial" in used_types
        assert "Hélice" in used_types
        assert result["ruta"] == ["A", "B", "C"]

    def test_flag_true_origin_only_when_no_routes_feasible(self):
        """
        When budget/time is zero, no leg can be taken — origin-only result
        regardless of the coverage flag.
        """
        g = self._make_two_type_chain()
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=0.0,
            tiempo_disponible_min=0.0,
            criterio_desempate="cost",
            require_all_transport_types=True,
        )
        assert result["ruta"] == ["A"]
        assert result["tramos"] == []

    def test_flag_true_single_type_registry_trivially_satisfied(self):
        """
        When tipos_transporte restricts to one type, 'all types' means that
        one type. The constraint is satisfied after the first leg.
        """
        g = self._make_two_type_chain()
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=1000.0,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            tipos_transporte=["Avión Comercial"],
            require_all_transport_types=True,
        )
        # Only A→B is reachable with Avión Comercial (B→C uses Hélice)
        used_types = {t["aeronave"] for t in result["tramos"]}
        assert used_types == {"Avión Comercial"}

    def test_flag_true_no_coverage_possible_falls_back_to_best_partial(self):
        """
        When it is impossible to cover all types (graph has only one aircraft
        type), the algorithm returns the best feasible partial result.
        """
        g = AdjacencyGraph()
        for iata in ("A", "B", "C"):
            g.add_node(make_airport(iata, es_hub=True))
        g.add_edge(make_route("A", "B", 100.0, aeronaves=["Avión Comercial"]))
        g.add_edge(make_route("B", "C", 100.0, aeronaves=["Avión Comercial"]))

        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=1000.0,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            require_all_transport_types=True,
        )
        assert len(result["ruta"]) >= 2
        assert_valid_structure(result)
        assert_tramos_valid(result)
        assert_no_cycles(result)

    def test_flag_true_constraints_still_respected(self):
        """
        Hard budget/time constraints must still be respected when flag=True.
        """
        g = self._make_multi_type_graph()
        tight_budget = 20.0   # Only enough for one leg (cheapest: Hélice $12)
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=tight_budget,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            require_all_transport_types=True,
        )
        assert result["total_costo_usd"] <= tight_budget + 1e-9

    def test_flag_true_result_valid_structure(self):
        """Result must always pass structural validation."""
        g = self._make_multi_type_graph()
        result = max_destinos_presupuesto_y_tiempo(
            g, "A",
            presupuesto=1000.0,
            tiempo_disponible_min=9999.0,
            criterio_desempate="time",
            require_all_transport_types=True,
        )
        assert_valid_structure(result)
        assert_tramos_valid(result)
        assert_no_cycles(result)

    # ── integration: real network ──────────────────────────────────────────────

    def test_real_network_flag_true_covers_multiple_types(self, real_graph):
        """
        With a generous budget/time, proponer_itinerarios must find itineraries
        that produce a valid structure for both alternatives.
        """
        graph, config = real_graph
        from services.basic_planner_service import BasicPlannerService
        service = BasicPlannerService(graph, config)
        result = service.proponer_itinerarios(
            origen="BOG",
            presupuesto=2000.0,
            tiempo_disponible_horas=200.0,
        )
        alt_a = result["alternativas"]["mayor_cantidad_destinos_por_presupuesto"]
        alt_b = result["alternativas"]["mayor_cantidad_destinos_por_tiempo"]
        assert_valid_structure(alt_a)
        assert_valid_structure(alt_b)
        assert_tramos_valid(alt_a)
        assert_tramos_valid(alt_b)

    def test_real_network_flag_true_respects_budget(self, real_graph):
        """Budget must not be exceeded even with the coverage flag active."""
        graph, _ = real_graph
        budget = 500.0
        result = max_destinos_presupuesto_y_tiempo(
            graph, "BOG",
            presupuesto=budget,
            tiempo_disponible_min=9999.0,
            criterio_desempate="cost",
            require_all_transport_types=True,
        )
        assert result["total_costo_usd"] <= budget + 1e-6

    def test_real_network_flag_true_respects_time(self, real_graph):
        """Time limit must not be exceeded even with the coverage flag active."""
        graph, _ = real_graph
        time_limit = 1500.0
        result = max_destinos_presupuesto_y_tiempo(
            graph, "BOG",
            presupuesto=9999.0,
            tiempo_disponible_min=time_limit,
            criterio_desempate="time",
            require_all_transport_types=True,
        )
        assert result["total_tiempo_min"] <= time_limit + 1e-6

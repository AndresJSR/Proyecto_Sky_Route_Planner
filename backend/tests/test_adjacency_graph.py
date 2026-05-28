"""
Tests for AdjacencyGraph (Persona 1 — R1, R4).

Covers: add_node, add_edge, get_neighbors, block_route, unblock_route,
        get_blocked_routes, hub/secondary filtering, degree queries.
"""

import pytest

from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def make_airport(iata: str, es_hub: bool = False) -> Airport:
    return Airport(
        id=iata, nombre=f"Airport {iata}", ciudad="City",
        pais="Country", zona_horaria="America/Bogota",
        es_hub=es_hub, costo_alojamiento=50.0, costo_alimentacion=10.0,
    )


def make_route(origen: str, destino: str, km: float = 500.0) -> Route:
    return Route(
        origen=origen, destino=destino, distancia_km=km,
        aeronaves=["Avión Comercial"], costo_base=1.0, estancia_minima=60,
    )


@pytest.fixture
def empty_graph() -> AdjacencyGraph:
    return AdjacencyGraph()


@pytest.fixture
def triangle_graph() -> AdjacencyGraph:
    """Graph with three airports: BOG(hub) → MDE → CTG → BOG."""
    g = AdjacencyGraph()
    g.add_node(make_airport("BOG", es_hub=True))
    g.add_node(make_airport("MDE"))
    g.add_node(make_airport("CTG"))
    g.add_edge(make_route("BOG", "MDE", 240))
    g.add_edge(make_route("MDE", "CTG", 550))
    g.add_edge(make_route("CTG", "BOG", 730))
    return g


# ──────────────────────────────────────────────
# Node operations
# ──────────────────────────────────────────────

class TestNodes:
    def test_add_node_increases_count(self, empty_graph):
        empty_graph.add_node(make_airport("BOG"))
        assert empty_graph.node_count() == 1

    def test_has_node_true_after_add(self, empty_graph):
        empty_graph.add_node(make_airport("LIM"))
        assert empty_graph.has_node("LIM") is True

    def test_has_node_false_when_absent(self, empty_graph):
        assert empty_graph.has_node("XYZ") is False

    def test_get_node_returns_airport(self, empty_graph):
        a = make_airport("SCL", es_hub=True)
        empty_graph.add_node(a)
        assert empty_graph.get_node("SCL") is a

    def test_get_node_raises_on_missing(self, empty_graph):
        with pytest.raises(KeyError):
            empty_graph.get_node("ZZZ")

    def test_duplicate_node_raises(self, empty_graph):
        empty_graph.add_node(make_airport("BOG"))
        with pytest.raises(ValueError, match="already exists"):
            empty_graph.add_node(make_airport("BOG"))

    def test_get_all_nodes_returns_all(self, triangle_graph):
        ids = {a.id for a in triangle_graph.get_all_nodes()}
        assert ids == {"BOG", "MDE", "CTG"}

    def test_get_hubs_only_returns_hubs(self, triangle_graph):
        hubs = triangle_graph.get_hubs()
        assert len(hubs) == 1
        assert hubs[0].id == "BOG"

    def test_get_secondary_airports(self, triangle_graph):
        secondary = triangle_graph.get_secondary_airports()
        ids = {a.id for a in secondary}
        assert ids == {"MDE", "CTG"}


# ──────────────────────────────────────────────
# Edge operations
# ──────────────────────────────────────────────

class TestEdges:
    def test_add_edge_increases_count(self, empty_graph):
        empty_graph.add_node(make_airport("BOG"))
        empty_graph.add_node(make_airport("MDE"))
        empty_graph.add_edge(make_route("BOG", "MDE"))
        assert empty_graph.edge_count() == 1

    def test_has_edge_true_after_add(self, triangle_graph):
        assert triangle_graph.has_edge("BOG", "MDE") is True

    def test_has_edge_false_reverse_not_declared(self, triangle_graph):
        # Graph is directed: MDE→BOG was NOT added
        assert triangle_graph.has_edge("MDE", "BOG") is False

    def test_get_route_returns_route(self, triangle_graph):
        r = triangle_graph.get_route("BOG", "MDE")
        assert r is not None
        assert r.distancia_km == 240

    def test_get_route_returns_none_for_absent(self, triangle_graph):
        assert triangle_graph.get_route("BOG", "CTG") is None

    def test_add_edge_unknown_origin_raises(self, empty_graph):
        empty_graph.add_node(make_airport("MDE"))
        with pytest.raises(KeyError, match="Origin airport"):
            empty_graph.add_edge(make_route("BOG", "MDE"))

    def test_add_edge_unknown_dest_raises(self, empty_graph):
        empty_graph.add_node(make_airport("BOG"))
        with pytest.raises(KeyError, match="Destination airport"):
            empty_graph.add_edge(make_route("BOG", "CTG"))

    def test_duplicate_edge_raises(self, triangle_graph):
        with pytest.raises(ValueError, match="already exists"):
            triangle_graph.add_edge(make_route("BOG", "MDE"))

    def test_get_all_edges_returns_all(self, triangle_graph):
        assert len(triangle_graph.get_all_edges()) == 3

    def test_out_degree(self, triangle_graph):
        assert triangle_graph.out_degree("BOG") == 1
        assert triangle_graph.out_degree("MDE") == 1

    def test_in_degree(self, triangle_graph):
        # CTG→BOG means BOG has in-degree 1
        assert triangle_graph.in_degree("BOG") == 1
        assert triangle_graph.in_degree("MDE") == 1

    def test_out_degree_unknown_raises(self, empty_graph):
        with pytest.raises(KeyError):
            empty_graph.out_degree("XXX")


# ──────────────────────────────────────────────
# get_neighbors — core algorithm interface
# ──────────────────────────────────────────────

class TestGetNeighbors:
    def test_returns_correct_neighbors(self, triangle_graph):
        neighbors = triangle_graph.get_neighbors("BOG")
        assert len(neighbors) == 1
        assert neighbors[0].destino == "MDE"

    def test_empty_neighbors_for_leaf(self, empty_graph):
        empty_graph.add_node(make_airport("BOG"))
        assert empty_graph.get_neighbors("BOG") == []

    def test_unknown_airport_raises(self, empty_graph):
        with pytest.raises(KeyError):
            empty_graph.get_neighbors("ZZZ")

    def test_blocked_route_excluded_by_default(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        neighbors = triangle_graph.get_neighbors("BOG")
        assert neighbors == []

    def test_blocked_route_included_when_flag_set(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        neighbors = triangle_graph.get_neighbors("BOG", include_blocked=True)
        assert len(neighbors) == 1

    def test_only_blocked_route_excluded_others_remain(self, empty_graph):
        """With two outgoing edges, only the blocked one is excluded."""
        empty_graph.add_node(make_airport("BOG"))
        empty_graph.add_node(make_airport("MDE"))
        empty_graph.add_node(make_airport("CTG"))
        empty_graph.add_edge(make_route("BOG", "MDE"))
        empty_graph.add_edge(make_route("BOG", "CTG"))
        empty_graph.block_route("BOG", "MDE")
        neighbors = empty_graph.get_neighbors("BOG")
        assert len(neighbors) == 1
        assert neighbors[0].destino == "CTG"


# ──────────────────────────────────────────────
# Route blocking / interruptions (R4)
# ──────────────────────────────────────────────

class TestRouteBlocking:
    def test_block_sets_flag(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        route = triangle_graph.get_route("BOG", "MDE")
        assert route.bloqueada is True

    def test_unblock_clears_flag(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        triangle_graph.unblock_route("BOG", "MDE")
        route = triangle_graph.get_route("BOG", "MDE")
        assert route.bloqueada is False

    def test_block_nonexistent_route_raises(self, triangle_graph):
        with pytest.raises(KeyError):
            triangle_graph.block_route("BOG", "CTG")

    def test_unblock_nonexistent_route_raises(self, triangle_graph):
        with pytest.raises(KeyError):
            triangle_graph.unblock_route("MDE", "BOG")

    def test_get_blocked_routes_empty_initially(self, triangle_graph):
        assert triangle_graph.get_blocked_routes() == []

    def test_get_blocked_routes_returns_blocked(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        blocked = triangle_graph.get_blocked_routes()
        assert len(blocked) == 1
        assert blocked[0].origen == "BOG"
        assert blocked[0].destino == "MDE"

    def test_blocking_does_not_remove_edge(self, triangle_graph):
        """Edge count must stay the same after blocking."""
        count_before = triangle_graph.edge_count()
        triangle_graph.block_route("BOG", "MDE")
        assert triangle_graph.edge_count() == count_before

    def test_block_multiple_routes(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        triangle_graph.block_route("MDE", "CTG")
        assert len(triangle_graph.get_blocked_routes()) == 2

    def test_unblock_restores_neighbor_visibility(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        triangle_graph.unblock_route("BOG", "MDE")
        neighbors = triangle_graph.get_neighbors("BOG")
        assert len(neighbors) == 1

    def test_graph_repr_reflects_blocked_count(self, triangle_graph):
        triangle_graph.block_route("BOG", "MDE")
        assert "blocked=1" in repr(triangle_graph)

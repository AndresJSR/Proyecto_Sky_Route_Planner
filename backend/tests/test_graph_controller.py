import os
import pytest

from infrastructure.json_loader import JSONLoader
from services.graph_service import GraphService
from interfaces.api.graph_controller import GraphController


@pytest.fixture
def real_network_graph_and_config():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "network.json")
    loader = JSONLoader()
    graph, config = loader.load(path)
    return graph, config


@pytest.fixture
def graph_service(real_network_graph_and_config):
    graph, _ = real_network_graph_and_config
    return GraphService(graph)


@pytest.fixture
def graph_controller(graph_service):
    return GraphController(graph_service)


def test_get_network_summary(graph_controller):
    resp = graph_controller.get_network_summary()
    assert resp["ok"] is True
    data = resp["data"]
    assert data["total_aeropuertos"] >= 30
    assert data["total_rutas"] > 0
    assert data["total_hubs"] > 0


def test_get_airports_and_hubs_filter(graph_controller):
    all_resp = graph_controller.get_airports()
    hubs_resp = graph_controller.get_airports({"solo_hubs": True})

    assert all_resp["ok"] is True
    assert hubs_resp["ok"] is True

    all_airports = all_resp["data"]
    hub_airports = hubs_resp["data"]

    assert len(hub_airports) <= len(all_airports)
    assert all(a.get("esHub", False) for a in hub_airports)


def test_get_airport_detail_bog(graph_controller):
    resp = graph_controller.get_airport_detail({"airport_id": "BOG"})
    assert resp["ok"] is True
    data = resp["data"]
    assert data["id"] == "BOG"
    assert "costoAlojamiento" in data
    assert "gradoSalida" in data


def test_get_routes_and_blocked(graph_controller):
    routes_resp = graph_controller.get_routes()
    routes_blocked_resp = graph_controller.get_routes({"include_blocked": True})
    blocked_list_resp = graph_controller.get_blocked_routes()

    assert routes_resp["ok"] and routes_blocked_resp["ok"] and blocked_list_resp["ok"]

    assert len(routes_blocked_resp["data"]) >= len(routes_resp["data"])
    assert isinstance(blocked_list_resp["data"], list)


def test_get_neighbors_and_existence_checks(graph_controller):
    neighbors_resp = graph_controller.get_neighbors({"airport_id": "BOG"})
    assert neighbors_resp["ok"] is True
    for r in neighbors_resp["data"]:
        assert r["origen"] == "BOG"

    exists_resp = graph_controller.airport_exists({"airport_id": "BOG"})
    assert exists_resp["ok"] is True
    assert exists_resp["data"]["exists"] is True

    not_exists_resp = graph_controller.airport_exists({"airport_id": "XXX"})
    assert not_exists_resp["ok"] is True
    assert not_exists_resp["data"]["exists"] is False

    route_exists = graph_controller.route_exists({"origen": "BOG", "destino": "MDE"})
    assert route_exists["ok"] is True


def test_validation_error_on_missing_field(graph_controller):
    resp = graph_controller.get_airport_detail({})
    assert resp["ok"] is False
    assert resp["error"]["type"] == "ValueError"

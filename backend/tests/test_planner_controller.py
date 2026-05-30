import os
import json
import tempfile

import pytest

from infrastructure.json_loader import JSONLoader
from services.basic_planner_service import BasicPlannerService
from interfaces.api.planner_controller import PlannerController


@pytest.fixture
def real_network_graph_and_config():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "network.json")
    loader = JSONLoader()
    graph, config = loader.load(path)
    return graph, config


@pytest.fixture
def planner_service(real_network_graph_and_config):
    graph, config = real_network_graph_and_config
    return BasicPlannerService(graph, config)


@pytest.fixture
def planner_controller(planner_service):
    return PlannerController(planner_service)


def test_calculate_optimal_route_and_multi_criteria(planner_controller):
    payload = {"origen": "BOG", "destino": "MDE", "criterio": "costo"}
    resp = planner_controller.calculate_optimal_route(payload)
    assert resp["ok"] is True
    data = resp["data"]
    assert data is not None
    assert "ruta" in data
    assert "total_costo_usd" in data or "total_distancia_km" in data

    multi_payload = {"origen": "BOG", "destino": "MDE", "criterios": ["costo", "tiempo"]}
    resp2 = planner_controller.calculate_routes_by_criteria(multi_payload)
    assert resp2["ok"] is True
    assert set(resp2["data"]["criterios"]) == {"cost", "time"}


def test_propose_itineraries_and_invalid_payloads(planner_controller):
    payload = {"origen": "BOG", "presupuesto": 1000, "tiempo_disponible_horas": 48}
    resp = planner_controller.propose_itineraries(payload)
    assert resp["ok"] is True
    data = resp["data"]
    assert "alternativas" in data
    assert "mayor_cantidad_destinos_por_presupuesto" in data["alternativas"]

    # Missing required field -> validation error
    bad = {}
    bad_resp = planner_controller.calculate_optimal_route(bad)
    assert bad_resp["ok"] is False
    assert bad_resp["error"]["type"] == "ValueError"


def test_negative_budget_raises(planner_controller):
    payload = {"origen": "BOG", "presupuesto": -10, "tiempo_disponible_horas": 10}
    resp = planner_controller.propose_itineraries(payload)
    assert resp["ok"] is False
    assert resp["error"]["type"] == "ValueError"


def test_subsidised_route_with_temp_network():
    # Build a minimal network with a subsidised route CLO -> GYE
    data = {
        "aeropuertos": [
            {"id": "CLO", "nombre": "CLO", "ciudad": "CLO", "pais": "CO", "zonaHoraria": "America/Bogota", "esHub": False, "costoAlojamiento": 10, "costoAlimentacion": 5, "actividades": [], "trabajos": []},
            {"id": "GYE", "nombre": "GYE", "ciudad": "GYE", "pais": "EC", "zonaHoraria": "America/Guayaquil", "esHub": False, "costoAlojamiento": 10, "costoAlimentacion": 5, "actividades": [], "trabajos": []},
        ],
        "rutas": [
            {"origen": "CLO", "destino": "GYE", "distanciaKm": 600, "aeronaves": ["Avión Regional"], "costoBase": 0, "estanciaMinima": 60}
        ]
    }

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, tmp, ensure_ascii=False)
    tmp.close()

    try:
        loader = JSONLoader()
        graph, config = loader.load(tmp.name)
        service = BasicPlannerService(graph, config)
        controller = PlannerController(service)

        resp = controller.calculate_optimal_route({"origen": "CLO", "destino": "GYE", "criterio": "costo"})
        assert resp["ok"] is True
        result = resp["data"]
        assert result is not None
        assert result["total_costo_usd"] == pytest.approx(0.0)
    finally:
        os.unlink(tmp.name)

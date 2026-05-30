"""
Tests for JSONLoader (Persona 1 — R1).

Covers: successful load, structural validation errors, aircraft rate overrides,
        config defaults, subsidised routes, activity/job parsing.
"""

import json
import os
import tempfile

import pytest

from infrastructure.json_loader import JSONLoader
from graph.adjacency_graph import AdjacencyGraph
from domain.models.activity import Activity


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _write_json(data: dict) -> str:
    """Write a dict as JSON to a temp file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tmp, ensure_ascii=False)
    tmp.close()
    return tmp.name


def _minimal_airport(iata: str, es_hub: bool = False) -> dict:
    return {
        "id": iata,
        "nombre": f"Airport {iata}",
        "ciudad": "City",
        "pais": "Country",
        "zonaHoraria": "America/Bogota",
        "esHub": es_hub,
        "costoAlojamiento": 50,
        "costoAlimentacion": 10,
        "actividades": [],
        "trabajos": [],
    }


def _minimal_route(origen: str, destino: str, km: float = 500.0) -> dict:
    return {
        "origen": origen,
        "destino": destino,
        "distanciaKm": km,
        "aeronaves": ["Avión Comercial"],
        "costoBase": 1,
        "estanciaMinima": 60,
    }


MINIMAL_NETWORK = {
    "aeropuertos": [
        _minimal_airport("BOG", es_hub=True),
        _minimal_airport("MDE"),
        _minimal_airport("CTG"),
    ],
    "rutas": [
        _minimal_route("BOG", "MDE", 240),
        _minimal_route("MDE", "CTG", 550),
        _minimal_route("CTG", "BOG", 730),
    ],
}


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def loader() -> JSONLoader:
    return JSONLoader()


@pytest.fixture
def network_file() -> str:
    path = _write_json(MINIMAL_NETWORK)
    yield path
    os.unlink(path)


@pytest.fixture
def real_network_file() -> str:
    """Path to the actual data/network.json used in the project."""
    return os.path.join(
        os.path.dirname(__file__), "..", "data", "network.json"
    )


# ──────────────────────────────────────────────
# Successful load
# ──────────────────────────────────────────────

class TestLoadSuccess:
    def test_returns_graph_and_config(self, loader, network_file):
        graph, config = loader.load(network_file)
        assert isinstance(graph, AdjacencyGraph)
        assert isinstance(config, dict)

    def test_correct_node_count(self, loader, network_file):
        graph, _ = loader.load(network_file)
        assert graph.node_count() == 3

    def test_correct_edge_count(self, loader, network_file):
        graph, _ = loader.load(network_file)
        assert graph.edge_count() == 3

    def test_hub_flag_set(self, loader, network_file):
        graph, _ = loader.load(network_file)
        assert graph.get_node("BOG").es_hub is True
        assert graph.get_node("MDE").es_hub is False

    def test_directed_graph_no_implicit_reverse(self, loader, network_file):
        """BOG→MDE exists but MDE→BOG must NOT exist (not declared)."""
        graph, _ = loader.load(network_file)
        assert graph.has_edge("BOG", "MDE") is True
        assert graph.has_edge("MDE", "BOG") is False

    def test_route_distance_correct(self, loader, network_file):
        graph, _ = loader.load(network_file)
        route = graph.get_route("BOG", "MDE")
        assert route.distancia_km == 240.0

    def test_iata_codes_uppercased(self, loader):
        data = {
            "aeropuertos": [_minimal_airport("bog"), _minimal_airport("mde")],
            "rutas": [_minimal_route("bog", "mde")],
        }
        path = _write_json(data)
        try:
            graph, _ = loader.load(path)
            assert graph.has_node("BOG")
            assert graph.has_edge("BOG", "MDE")
        finally:
            os.unlink(path)

    def test_subsidised_route_flag(self, loader):
        data = {
            "aeropuertos": [_minimal_airport("CLO"), _minimal_airport("GYE")],
            "rutas": [{
                "origen": "CLO", "destino": "GYE", "distanciaKm": 600,
                "aeronaves": ["Avión Regional"], "costoBase": 0, "estanciaMinima": 60,
            }],
        }
        path = _write_json(data)
        try:
            graph, _ = loader.load(path)
            assert graph.get_route("CLO", "GYE").es_subsidiada is True
        finally:
            os.unlink(path)

    def test_real_network_loads(self, loader, real_network_file):
        graph, config = loader.load(real_network_file)
        assert graph.node_count() >= 30
        assert graph.edge_count() > 0

    def test_real_network_has_hubs(self, loader, real_network_file):
        graph, _ = loader.load(real_network_file)
        assert len(graph.get_hubs()) > 0

    def test_real_network_bog_is_hub(self, loader, real_network_file):
        graph, _ = loader.load(real_network_file)
        assert graph.get_node("BOG").es_hub is True


# ──────────────────────────────────────────────
# Activities and jobs parsing
# ──────────────────────────────────────────────

class TestActivitiesAndJobs:
    def test_activities_parsed(self, loader):
        data = {
            "aeropuertos": [{
                **_minimal_airport("BOG"),
                "actividades": [
                    {"nombre": "Tour", "tipo": "opcional", "duracionMin": 120, "costoUSD": 15}
                ],
            }, _minimal_airport("MDE")],
            "rutas": [_minimal_route("BOG", "MDE")],
        }
        path = _write_json(data)
        try:
            graph, _ = loader.load(path)
            assert len(graph.get_node("BOG").actividades) == 1
            act = graph.get_node("BOG").actividades[0]
            assert act.nombre == "Tour"
            assert act.tipo == Activity.TIPO_OPCIONAL
            assert act.duracion_min == 120
            assert act.costo_usd == 15.0
        finally:
            os.unlink(path)

    def test_jobs_parsed(self, loader):
        data = {
            "aeropuertos": [{
                **_minimal_airport("BOG"),
                "trabajos": [
                    {"nombre": "Cargador", "tarifaHora": 6, "maxHoras": 8}
                ],
            }, _minimal_airport("MDE")],
            "rutas": [_minimal_route("BOG", "MDE")],
        }
        path = _write_json(data)
        try:
            graph, _ = loader.load(path)
            assert len(graph.get_node("BOG").trabajos) == 1
            job = graph.get_node("BOG").trabajos[0]
            assert job.nombre == "Cargador"
            assert job.tarifa_hora == 6.0
            assert job.max_horas == 8
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────
# Config defaults and overrides
# ──────────────────────────────────────────────

class TestConfig:
    def test_default_config_values(self, loader, network_file):
        _, config = loader.load(network_file)
        assert config["presupuestoMinimoPorc"] == 35
        assert config["intervaloAlojamiento"] == 20
        assert config["intervaloAlimentacion"] == 8

    def test_default_aircraft_rates(self, loader, network_file):
        _, config = loader.load(network_file)
        assert config["aeronaves"]["Avión Comercial"]["costo_km"] == 0.18
        assert config["aeronaves"]["Avión Regional"]["costo_km"] == 0.25
        assert config["aeronaves"]["Hélice"]["costo_km"] == 0.12

    def test_config_override_aircraft_rates(self, loader):
        data = {
            **MINIMAL_NETWORK,
            "config": {
                "aeronaves": {
                    "Avión Comercial": {"costoKm": 0.99, "tiempoKm": 0.5}
                }
            },
        }
        path = _write_json(data)
        try:
            _, config = loader.load(path)
            assert config["aeronaves"]["Avión Comercial"]["costo_km"] == 0.99
            assert config["aeronaves"]["Avión Comercial"]["tiempo_km"] == 0.5
            # Unspecified types keep defaults
            assert config["aeronaves"]["Hélice"]["costo_km"] == 0.12
        finally:
            os.unlink(path)

    def test_config_override_thresholds(self, loader):
        data = {
            **MINIMAL_NETWORK,
            "config": {
                "presupuestoMinimoPorc": 40,
                "intervaloAlojamiento": 24,
                "intervaloAlimentacion": 6,
            },
        }
        path = _write_json(data)
        try:
            _, config = loader.load(path)
            assert config["presupuestoMinimoPorc"] == 40
            assert config["intervaloAlojamiento"] == 24
            assert config["intervaloAlimentacion"] == 6
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────
# Validation errors
# ──────────────────────────────────────────────

class TestValidationErrors:
    def test_file_not_found_raises(self, loader):
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load("nonexistent_file.json")

    def test_malformed_json_raises(self, loader):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp.write("{ this is not valid json }")
        tmp.close()
        try:
            with pytest.raises(ValueError, match="Malformed JSON"):
                loader.load(tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_missing_aeropuertos_key_raises(self, loader):
        path = _write_json({"rutas": []})
        try:
            with pytest.raises(ValueError, match="aeropuertos"):
                loader.load(path)
        finally:
            os.unlink(path)

    def test_missing_rutas_key_raises(self, loader):
        path = _write_json({"aeropuertos": []})
        try:
            with pytest.raises(ValueError, match="rutas"):
                loader.load(path)
        finally:
            os.unlink(path)

    def test_airport_missing_required_field_raises(self, loader):
        data = {
            "aeropuertos": [{"id": "BOG"}],  # missing most fields
            "rutas": [],
        }
        path = _write_json(data)
        try:
            with pytest.raises(ValueError, match="missing required fields"):
                loader.load(path)
        finally:
            os.unlink(path)

    def test_route_missing_required_field_raises(self, loader):
        data = {
            "aeropuertos": [_minimal_airport("BOG"), _minimal_airport("MDE")],
            "rutas": [{"origen": "BOG"}],  # missing destino, distanciaKm, aeronaves
        }
        path = _write_json(data)
        try:
            with pytest.raises(ValueError, match="missing required fields"):
                loader.load(path)
        finally:
            os.unlink(path)

    def test_route_with_unknown_aircraft_raises(self, loader):
        data = {
            "aeropuertos": [_minimal_airport("BOG"), _minimal_airport("MDE")],
            "rutas": [{
                "origen": "BOG", "destino": "MDE", "distanciaKm": 240,
                "aeronaves": ["Boeing 777X"],
            }],
        }
        path = _write_json(data)
        try:
            with pytest.raises(ValueError, match="Unknown aircraft type"):
                loader.load(path)
        finally:
            os.unlink(path)

    def test_route_references_missing_airport_raises(self, loader):
        data = {
            "aeropuertos": [_minimal_airport("BOG")],
            "rutas": [_minimal_route("BOG", "LIM")],  # LIM not in nodes
        }
        path = _write_json(data)
        try:
            with pytest.raises(ValueError, match="Error adding route"):
                loader.load(path)
        finally:
            os.unlink(path)

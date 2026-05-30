import pytest

from algorithms.backtracking import max_destinos_presupuesto, max_destinos_tiempo
from algorithms.dijkstra import dijkstra
from algorithms.shared import normalize_criterion
from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph
from services.basic_planner_service import BasicPlannerService


def make_airport(iata: str, es_hub: bool = True) -> Airport:
    return Airport(
        id=iata,
        nombre=f"Airport {iata}",
        ciudad="City",
        pais="Country",
        zona_horaria="America/Bogota",
        es_hub=es_hub,
        costo_alojamiento=50.0,
        costo_alimentacion=10.0,
    )


def make_route(
    origen: str,
    destino: str,
    km: float,
    aeronaves: list[str] | None = None,
    costo_base: float = 1.0,
) -> Route:
    return Route(
        origen=origen,
        destino=destino,
        distancia_km=km,
        aeronaves=aeronaves or ["Avión Comercial"],
        costo_base=costo_base,
        estancia_minima=60,
    )


@pytest.fixture
def planner_graph() -> AdjacencyGraph:
    g = AdjacencyGraph()
    g.add_node(make_airport("A", es_hub=True))
    g.add_node(make_airport("B", es_hub=True))
    g.add_node(make_airport("C", es_hub=False))
    g.add_node(make_airport("D", es_hub=True))

    g.add_edge(make_route("A", "B", 100.0, costo_base=0.0))
    g.add_edge(make_route("B", "D", 100.0))
    g.add_edge(make_route("A", "C", 70.0))
    g.add_edge(make_route("C", "D", 70.0))
    return g


@pytest.fixture
def planner_service(planner_graph: AdjacencyGraph) -> BasicPlannerService:
    return BasicPlannerService(planner_graph)


def test_calcular_ruta_optima_costo(planner_service: BasicPlannerService):
    result = planner_service.calcular_ruta_optima("A", "D", "costo")

    assert result is not None
    assert result["ruta"] == ["A", "B", "D"]
    assert result["total_costo_usd"] == pytest.approx(18.0)
    assert result["total_distancia_km"] == pytest.approx(200.0)


def test_calcular_ruta_optima_tiempo(planner_service: BasicPlannerService):
    result = planner_service.calcular_ruta_optima("A", "D", "tiempo")

    assert result is not None
    assert result["ruta"] == ["A", "C", "D"]
    assert result["total_tiempo_min"] == pytest.approx(98.0)


def test_calcular_ruta_optima_distancia(planner_service: BasicPlannerService):
    result = planner_service.calcular_ruta_optima("A", "D", "distancia")

    assert result is not None
    assert result["ruta"] == ["A", "C", "D"]
    assert result["total_distancia_km"] == pytest.approx(140.0)


def test_calcular_rutas_por_criterios_returns_one_result_per_criterion(
    planner_service: BasicPlannerService,
):
    result = planner_service.calcular_rutas_por_criterios(
        "A",
        "D",
        ["costo", "tiempo", "distancia"],
    )

    assert result["criterios"] == ["cost", "time", "distance"]
    assert set(result["resultados"].keys()) == {"cost", "time", "distance"}
    assert result["resultados"]["cost"]["ruta"] == ["A", "B", "D"]
    assert result["resultados"]["time"]["ruta"] == ["A", "C", "D"]
    assert result["resultados"]["distance"]["ruta"] == ["A", "C", "D"]


def test_proponer_itinerarios_returns_two_alternatives(
    planner_service: BasicPlannerService,
    planner_graph: AdjacencyGraph,
):
    result = planner_service.proponer_itinerarios(
        "A",
        presupuesto=30.0,
        tiempo_disponible_horas=3.0,
    )

    assert result["origen"] == "A"
    assert result["restricciones"]["tiempo_disponible_min"] == pytest.approx(180.0)

    budget_expected = max_destinos_presupuesto(
        graph=planner_graph,
        origen="A",
        presupuesto=30.0,
        incluir_secundarios=True,
        tipos_transporte=None,
    )
    time_expected = max_destinos_tiempo(
        graph=planner_graph,
        origen="A",
        tiempo_disponible_min=180.0,
        incluir_secundarios=True,
        tipos_transporte=None,
    )

    assert result["alternativas"]["mayor_cantidad_destinos_por_presupuesto"] == budget_expected
    assert result["alternativas"]["mayor_cantidad_destinos_por_tiempo"] == time_expected


def test_calcular_ruta_optima_invalid_origin_raises(planner_service: BasicPlannerService):
    with pytest.raises(KeyError):
        planner_service.calcular_ruta_optima("X", "D", "costo")


def test_calcular_ruta_optima_invalid_destination_raises(
    planner_service: BasicPlannerService,
):
    with pytest.raises(KeyError):
        planner_service.calcular_ruta_optima("A", "X", "costo")


def test_calcular_ruta_optima_empty_transport_types_raises(
    planner_service: BasicPlannerService,
):
    with pytest.raises(ValueError):
        planner_service.calcular_ruta_optima(
            "A",
            "D",
            "costo",
            tipos_transporte=[],
        )
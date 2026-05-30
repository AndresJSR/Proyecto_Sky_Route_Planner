from __future__ import annotations

from pathlib import Path
from pprint import pprint

from infrastructure.json_loader import JSONLoader
from interfaces.api.graph_controller import GraphController
from interfaces.api.planner_controller import PlannerController
from services.basic_planner_service import BasicPlannerService
from services.graph_service import GraphService


def print_section(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def print_response(title: str, response: dict) -> None:
    print_section(title)
    print(f"OK: {response.get('ok')}")

    if not response.get("ok"):
        print("ERROR:")
        pprint(response.get("error"))
        return

    data = response.get("data")

    if isinstance(data, list):
        print(f"Items retornados: {len(data)}")
        pprint(data[:3])
        return

    pprint(data)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    network_path = base_dir / "data" / "network.json"

    loader = JSONLoader()
    graph, config = loader.load(str(network_path))

    graph_service = GraphService(graph)
    basic_planner_service = BasicPlannerService(graph, config)

    graph_controller = GraphController(graph_service)
    planner_controller = PlannerController(basic_planner_service)

    print_section("SkyRoute Planner - Controller check with network.json")
    print(f"Network file: {network_path}")

    # ------------------------------------------------------------------
    # GraphController checks
    # ------------------------------------------------------------------

    print_response(
        "GraphController - Network summary",
        graph_controller.get_network_summary(),
    )

    print_response(
        "GraphController - All airports",
        graph_controller.get_airports({"solo_hubs": False}),
    )

    print_response(
        "GraphController - Hub airports only",
        graph_controller.get_airports({"solo_hubs": True}),
    )

    print_response(
        "GraphController - Airport detail BOG",
        graph_controller.get_airport_detail({"airport_id": "BOG"}),
    )

    print_response(
        "GraphController - All routes",
        graph_controller.get_routes({"include_blocked": True}),
    )

    print_response(
        "GraphController - Routes from BOG",
        graph_controller.get_neighbors(
            {
                "airport_id": "BOG",
                "include_blocked": False,
            }
        ),
    )

    print_response(
        "GraphController - Airport exists BOG",
        graph_controller.airport_exists({"airport_id": "BOG"}),
    )

    print_response(
        "GraphController - Route exists BOG -> MDE",
        graph_controller.route_exists(
            {
                "origen": "BOG",
                "destino": "MDE",
            }
        ),
    )

    print_response(
        "GraphController - Blocked routes",
        graph_controller.get_blocked_routes(),
    )

    # ------------------------------------------------------------------
    # PlannerController checks
    # ------------------------------------------------------------------

    print_response(
        "PlannerController - Optimal route BOG -> SCL by cost",
        planner_controller.calculate_optimal_route(
            {
                "origen": "BOG",
                "destino": "SCL",
                "criterio": "costo",
                "incluir_secundarios": True,
                "tipos_transporte": None,
            }
        ),
    )

    print_response(
        "PlannerController - Routes BOG -> SCL by multiple criteria",
        planner_controller.calculate_routes_by_criteria(
            {
                "origen": "BOG",
                "destino": "SCL",
                "criterios": ["costo", "tiempo", "distancia"],
                "incluir_secundarios": True,
                "tipos_transporte": None,
            }
        ),
    )

    print_response(
        "PlannerController - Proposed itineraries from BOG",
        planner_controller.propose_itineraries(
            {
                "origen": "BOG",
                "presupuesto": 700,
                "tiempo_disponible_horas": 72,
                "incluir_secundarios": True,
                "tipos_transporte": None,
            }
        ),
    )

    print_response(
        "PlannerController - Optimal route CLO -> GYE by cost, subsidized route",
        planner_controller.calculate_optimal_route(
            {
                "origen": "CLO",
                "destino": "GYE",
                "criterio": "costo",
                "incluir_secundarios": True,
                "tipos_transporte": None,
            }
        ),
    )

    # ------------------------------------------------------------------
    # Error checks
    # ------------------------------------------------------------------

    print_response(
        "PlannerController - Error check: invalid airport",
        planner_controller.calculate_optimal_route(
            {
                "origen": "XXX",
                "destino": "SCL",
                "criterio": "costo",
                "incluir_secundarios": True,
                "tipos_transporte": None,
            }
        ),
    )

    print_response(
        "GraphController - Error check: missing airport_id",
        graph_controller.get_airport_detail({}),
    )


if __name__ == "__main__":
    main()
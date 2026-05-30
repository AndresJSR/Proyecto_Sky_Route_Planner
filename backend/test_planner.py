from __future__ import annotations

from infrastructure.json_loader import JSONLoader
from services.basic_planner_service import BasicPlannerService


def print_result(title: str, result: dict | None) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if result is None:
        print("No se encontró una ruta posible.")
        return

    print(f"Ruta: {' -> '.join(result.get('ruta', []))}")
    print(f"Cantidad destinos: {result.get('cantidad_destinos', 0)}")
    print(f"Distancia total: {result.get('total_distancia_km', 0)} km")
    print(f"Costo total: ${result.get('total_costo_usd', 0)} USD")
    print(f"Tiempo total: {result.get('total_tiempo_min', 0)} min")

    print("\nTramos:")
    for tramo in result.get("tramos", []):
        print(
            f"  {tramo['origen']} -> {tramo['destino']} | "
            f"{tramo['aeronave']} | "
            f"{tramo['distancia_km']} km | "
            f"${tramo['costo_usd']} USD | "
            f"{tramo['tiempo_min']} min | "
            f"Subsidiada: {tramo.get('subsidiada', False)}"
        )


def main() -> None:
    loader = JSONLoader()
    graph, config = loader.load("./backend/data/network.json")

    service = BasicPlannerService(graph, config)

    print("\nSkyRoute Planner - prueba real con network.json")
    print(f"Aeropuertos cargados: {graph.node_count()}")
    print(f"Rutas cargadas: {graph.edge_count()}")
    print(f"Hubs: {len(graph.get_hubs())}")
    print(f"Secundarios: {len(graph.get_secondary_airports())}")

    # 1. Ruta óptima por costo
    result_cost = service.calcular_ruta_optima(
        origen="BOG",
        destino="SCL",
        criterio="costo",
        incluir_secundarios=True,
        tipos_transporte=None,
    )
    print_result("Ruta óptima BOG -> SCL por COSTO", result_cost)

    # 2. Ruta óptima por tiempo
    result_time = service.calcular_ruta_optima(
        origen="BOG",
        destino="SCL",
        criterio="tiempo",
        incluir_secundarios=True,
        tipos_transporte=None,
    )
    print_result("Ruta óptima BOG -> SCL por TIEMPO", result_time)

    # 3. Ruta óptima por distancia
    result_distance = service.calcular_ruta_optima(
        origen="BOG",
        destino="SCL",
        criterio="distancia",
        incluir_secundarios=True,
        tipos_transporte=None,
    )
    print_result("Ruta óptima BOG -> SCL por DISTANCIA", result_distance)

    # 4. Varias rutas por criterios
    multi_results = service.calcular_rutas_por_criterios(
        origen="BOG",
        destino="SCL",
        criterios=["costo", "tiempo", "distancia"],
        incluir_secundarios=True,
        tipos_transporte=None,
    )

    print("\n" + "=" * 80)
    print("Rutas por múltiples criterios")
    print("=" * 80)
    for criterion, result in multi_results["resultados"].items():
        print_result(f"Criterio: {criterion.upper()}", result)

    # 5. Proponer itinerarios por presupuesto y tiempo
    itineraries = service.proponer_itinerarios(
        origen="BOG",
        presupuesto=700,
        tiempo_disponible_horas=72,
        incluir_secundarios=True,
        tipos_transporte=None,
    )

    print("\n" + "=" * 80)
    print("Propuesta de itinerarios desde BOG")
    print("=" * 80)

    print_result(
        "Mayor cantidad de destinos por PRESUPUESTO",
        itineraries["alternativas"]["mayor_cantidad_destinos_por_presupuesto"],
    )

    print_result(
        "Mayor cantidad de destinos por TIEMPO",
        itineraries["alternativas"]["mayor_cantidad_destinos_por_tiempo"],
    )

    # 6. Prueba excluyendo aeropuertos secundarios
    result_only_hubs = service.calcular_ruta_optima(
        origen="BOG",
        destino="SCL",
        criterio="costo",
        incluir_secundarios=False,
        tipos_transporte=None,
    )
    print_result("Ruta BOG -> SCL por COSTO excluyendo secundarios", result_only_hubs)

    # 7. Prueba filtrando por tipo de transporte
    result_commercial_only = service.calcular_ruta_optima(
        origen="BOG",
        destino="SCL",
        criterio="tiempo",
        incluir_secundarios=True,
        tipos_transporte=["Avión Comercial"],
    )
    print_result("Ruta BOG -> SCL solo con Avión Comercial", result_commercial_only)

    # 8. Prueba de ruta subsidiada
    result_subsidized = service.calcular_ruta_optima(
        origen="CLO",
        destino="GYE",
        criterio="costo",
        incluir_secundarios=True,
        tipos_transporte=None,
    )
    print_result("Ruta subsidiada CLO -> GYE por COSTO", result_subsidized)


if __name__ == "__main__":
    main()
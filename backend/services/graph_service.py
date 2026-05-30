"""
Graph service.

Responsibility
--------------
This service exposes read-only query operations over the AdjacencyGraph.

It is used by API/controllers and frontend adapters to retrieve graph data
without exposing the internal graph structure directly.

This service does not implement path-finding algorithms.
"""

from __future__ import annotations

from typing import Any

from domain.models.airport import Airport
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph


class GraphService:
    """Exposes read-only query operations on the AdjacencyGraph."""

    def __init__(self, graph: AdjacencyGraph) -> None:
        self.graph = graph

    def obtener_info_aeropuerto(self, airport_id: str) -> dict[str, Any]:
        """
        Return full information for a given airport node.

        Args:
            airport_id: IATA airport code.

        Raises:
            KeyError: If the airport does not exist.
        """
        airport = self.graph.get_node(airport_id.upper())
        return self._serialize_airport_detail(airport)

    def listar_aeropuertos(self, solo_hubs: bool = False) -> list[dict[str, Any]]:
        """
        Return all airports, optionally filtered to hubs only.

        Args:
            solo_hubs: If True, only hub airports are returned.
        """
        airports = self.graph.get_hubs() if solo_hubs else self.graph.get_all_nodes()
        return [self._serialize_airport_summary(airport) for airport in airports]

    def listar_rutas(self, include_blocked: bool = False) -> list[dict[str, Any]]:
        """
        Return all routes, optionally including blocked ones.

        Args:
            include_blocked: If True, blocked routes are included.
        """
        routes = self.graph.get_all_edges(include_blocked=include_blocked)
        return [self._serialize_route(route) for route in routes]

    def obtener_rutas_desde(
        self,
        airport_id: str,
        include_blocked: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return all outgoing routes from a specific airport.

        Args:
            airport_id: IATA airport code.
            include_blocked: If True, blocked routes are included.

        Raises:
            KeyError: If the airport does not exist.
        """
        routes = self.graph.get_neighbors(
            airport_id=airport_id.upper(),
            include_blocked=include_blocked,
        )
        return [self._serialize_route(route) for route in routes]

    def obtener_resumen_red(self) -> dict[str, Any]:
        """
        Return general statistics about the graph.
        """
        return {
            "total_aeropuertos": self.graph.node_count(),
            "total_rutas": self.graph.edge_count(),
            "total_hubs": len(self.graph.get_hubs()),
            "total_secundarios": len(self.graph.get_secondary_airports()),
            "total_rutas_bloqueadas": len(self.graph.get_blocked_routes()),
        }

    def existe_aeropuerto(self, airport_id: str) -> bool:
        """
        Return True if the airport exists in the graph.
        """
        return self.graph.has_node(airport_id.upper())

    def existe_ruta(self, origen: str, destino: str) -> bool:
        """
        Return True if a direct route exists from origin to destination.
        """
        return self.graph.has_edge(origen.upper(), destino.upper())

    def listar_rutas_bloqueadas(self) -> list[dict[str, Any]]:
        """
        Return all currently blocked routes.
        """
        return [
            self._serialize_route(route)
            for route in self.graph.get_blocked_routes()
        ]

    # ------------------------------------------------------------------
    # Serializers
    # ------------------------------------------------------------------

    def _serialize_airport_summary(self, airport: Airport) -> dict[str, Any]:
        """
        Serialize basic airport information.
        """
        return {
            "id": airport.id,
            "nombre": airport.nombre,
            "ciudad": airport.ciudad,
            "pais": airport.pais,
            "zonaHoraria": airport.zona_horaria,
            "esHub": airport.es_hub,
        }

    def _serialize_airport_detail(self, airport: Airport) -> dict[str, Any]:
        """
        Serialize full airport information.
        """
        return {
            "id": airport.id,
            "nombre": airport.nombre,
            "ciudad": airport.ciudad,
            "pais": airport.pais,
            "zonaHoraria": airport.zona_horaria,
            "esHub": airport.es_hub,
            "costoAlojamiento": airport.costo_alojamiento,
            "costoAlimentacion": airport.costo_alimentacion,
            "aerolineas": list(getattr(airport, "aerolineas", [])),
            "actividades": [
                self._serialize_activity(activity)
                for activity in getattr(airport, "actividades", [])
            ],
            "trabajos": [
                self._serialize_job(job)
                for job in getattr(airport, "trabajos", [])
            ],
            "gradoSalida": self.graph.out_degree(airport.id),
            "gradoEntrada": self.graph.in_degree(airport.id),
        }

    def _serialize_route(self, route: Route) -> dict[str, Any]:
        """
        Serialize route information.
        """
        return {
            "origen": route.origen,
            "destino": route.destino,
            "distanciaKm": route.distancia_km,
            "aeronaves": list(route.aeronaves),
            "costoBase": route.costo_base,
            "estanciaMinima": route.estancia_minima,
            "bloqueada": route.bloqueada,
            "subsidiada": route.es_subsidiada,
        }

    def _serialize_activity(self, activity: Any) -> dict[str, Any]:
        """
        Serialize activity information.
        """
        return {
            "nombre": activity.nombre,
            "tipo": activity.tipo,
            "duracionMin": activity.duracion_min,
            "costoUSD": activity.costo_usd,
        }

    def _serialize_job(self, job: Any) -> dict[str, Any]:
        """
        Serialize job information.
        """
        return {
            "nombre": job.nombre,
            "tarifaHora": job.tarifa_hora,
            "maxHoras": job.max_horas,
        }
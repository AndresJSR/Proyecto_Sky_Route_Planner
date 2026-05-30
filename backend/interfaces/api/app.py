"""
SkyRoute Planner API.

This module defines the FastAPI application and exposes HTTP routes for
graph queries and basic planning operations.

The app uses controller classes instead of calling services directly. This
keeps the API layer separated from the application logic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend root is available when this module is imported by uvicorn.
BACKEND_DIR = Path(__file__).resolve().parents[2]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from infrastructure.json_loader import JSONLoader
from interfaces.api.graph_controller import GraphController
from interfaces.api.planner_controller import PlannerController
from services.basic_planner_service import BasicPlannerService
from services.graph_service import GraphService


NETWORK_PATH = BACKEND_DIR / "data" / "network.json"


def create_app() -> FastAPI:
    """
    Create and configure the SkyRoute Planner FastAPI application.

    The graph is loaded once when the API starts. Controllers then reuse
    the same graph instance through the service layer.
    """
    app = FastAPI(
        title="SkyRoute Planner API",
        version="1.0.0",
        description="Backend API for graph queries and basic route planning.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Development mode. Restrict in production.
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    loader = JSONLoader()
    graph, config = loader.load(str(NETWORK_PATH))

    graph_service = GraphService(graph)
    planner_service = BasicPlannerService(graph, config)

    graph_controller = GraphController(graph_service)
    planner_controller = PlannerController(planner_service)

    # ------------------------------------------------------------------
    # Health endpoints
    # ------------------------------------------------------------------

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "ok": True,
            "message": "SkyRoute Planner API is running.",
        }

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "network_file": str(NETWORK_PATH),
            "airports": graph.node_count(),
            "routes": graph.edge_count(),
        }

    # ------------------------------------------------------------------
    # Graph endpoints
    # ------------------------------------------------------------------

    @app.get("/graph/summary")
    def get_network_summary() -> dict[str, Any]:
        return graph_controller.get_network_summary()

    @app.get("/graph/airports")
    def get_airports(solo_hubs: bool = False) -> dict[str, Any]:
        return graph_controller.get_airports(
            {
                "solo_hubs": solo_hubs,
            }
        )

    @app.get("/graph/airports/{airport_id}")
    def get_airport_detail(airport_id: str) -> dict[str, Any]:
        return graph_controller.get_airport_detail(
            {
                "airport_id": airport_id,
            }
        )

    @app.get("/graph/routes")
    def get_routes(include_blocked: bool = False) -> dict[str, Any]:
        return graph_controller.get_routes(
            {
                "include_blocked": include_blocked,
            }
        )

    @app.get("/graph/airports/{airport_id}/neighbors")
    def get_neighbors(
        airport_id: str,
        include_blocked: bool = False,
    ) -> dict[str, Any]:
        return graph_controller.get_neighbors(
            {
                "airport_id": airport_id,
                "include_blocked": include_blocked,
            }
        )

    @app.get("/graph/blocked-routes")
    def get_blocked_routes() -> dict[str, Any]:
        return graph_controller.get_blocked_routes()

    @app.get("/graph/airports/{airport_id}/exists")
    def airport_exists(airport_id: str) -> dict[str, Any]:
        return graph_controller.airport_exists(
            {
                "airport_id": airport_id,
            }
        )

    @app.get("/graph/routes/exists")
    def route_exists(origen: str, destino: str) -> dict[str, Any]:
        return graph_controller.route_exists(
            {
                "origen": origen,
                "destino": destino,
            }
        )

    # ------------------------------------------------------------------
    # Basic planner endpoints
    # ------------------------------------------------------------------

    @app.post("/planner/optimal-route")
    def calculate_optimal_route(payload: dict[str, Any]) -> dict[str, Any]:
        return planner_controller.calculate_optimal_route(payload)

    @app.post("/planner/routes-by-criteria")
    def calculate_routes_by_criteria(payload: dict[str, Any]) -> dict[str, Any]:
        return planner_controller.calculate_routes_by_criteria(payload)

    @app.post("/planner/itineraries")
    def propose_itineraries(payload: dict[str, Any]) -> dict[str, Any]:
        return planner_controller.propose_itineraries(payload)

    return app


app = create_app()
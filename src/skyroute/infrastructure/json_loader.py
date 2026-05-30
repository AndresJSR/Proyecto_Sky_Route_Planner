"""JSON loading utilities for the air route graph."""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.models import Airport, Route
from ..graph import AirRouteGraph
from .json_validator import JsonValidator


class JsonLoader:
    """Loads graph data from JSON files."""

    def __init__(self, validator: JsonValidator | None = None) -> None:
        self.validator = validator or JsonValidator()

    def load_graph_from_file(self, file_path: str) -> AirRouteGraph:
        """Load a graph from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.validator.validate_graph_payload(payload)

        graph = AirRouteGraph()
        for airport_data in payload.get("airports", []):
            graph.add_airport(
                Airport(
                    code=airport_data["code"],
                    name=airport_data["name"],
                    city=airport_data["city"],
                    country=airport_data["country"],
                    latitude=airport_data.get("latitude"),
                    longitude=airport_data.get("longitude"),
                )
            )

        for route_data in payload.get("routes", []):
            graph.add_route(
                Route(
                    origin_code=route_data["origin_code"],
                    destination_code=route_data["destination_code"],
                    distance_km=route_data["distance_km"],
                    duration_minutes=route_data["duration_minutes"],
                    cost_usd=route_data["cost_usd"],
                )
            )

        return graph

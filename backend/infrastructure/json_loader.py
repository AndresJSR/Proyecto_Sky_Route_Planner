from __future__ import annotations

import json
import os
from typing import Any

from domain.models.activity import Activity
from domain.models.aircraft import Aircraft, DEFAULT_AIRCRAFT
from domain.models.airport import Airport
from domain.models.job import Job
from domain.models.route import Route
from graph.adjacency_graph import AdjacencyGraph

# Minimum required fields for structural validation
_REQUIRED_NODE_FIELDS: frozenset[str] = frozenset({
    "id", "nombre", "ciudad", "pais", "zonaHoraria",
    "esHub", "costoAlojamiento", "costoAlimentacion",
})
_REQUIRED_EDGE_FIELDS: frozenset[str] = frozenset({
    "origen", "destino", "distanciaKm", "aeronaves",
})


class JSONLoader:
    """
    Loads and validates a SkyRoute flight network from a JSON file.

    The JSON must contain:
        aeropuertos  — list of airport (node) objects
        rutas        — list of route (edge) objects
        config       — optional section to override default aircraft rates
                       and traveler rule thresholds

    Returns a populated AdjacencyGraph and the resolved config dict so
    that services can read the operative thresholds (e.g.
    presupuestoMinimoPorc, intervaloAlojamiento).

    Usage
    -----
        loader = JSONLoader()
        graph, config = loader.load("data/network.json")
    """

    def load(self, filepath: str) -> tuple[AdjacencyGraph, dict]:
        """
        Parse, validate, and build the flight network graph from a JSON file.

        Args:
            filepath: Path to the JSON file (absolute or relative).

        Returns:
            A tuple of (AdjacencyGraph, config_dict).

        Raises:
            FileNotFoundError: If the JSON file does not exist.
            ValueError:        If the JSON structure fails validation.
        """
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Network JSON file not found: '{filepath}'")

        with open(filepath, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Malformed JSON: {exc}") from exc

        self._validate(data)

        config = self._build_config(data.get("config", {}))
        aircraft_registry = self._build_aircraft_registry(config)

        graph = AdjacencyGraph()

        for node_data in data["aeropuertos"]:
            airport = self._build_airport(node_data)
            graph.add_node(airport)

        for edge_data in data["rutas"]:
            route = self._build_route(edge_data, aircraft_registry)
            try:
                graph.add_edge(route)
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Error adding route to graph: {exc}") from exc

        return graph, config

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, data: Any) -> None:
        """
        Perform structural validation of the raw JSON data.

        Raises:
            ValueError on any structural problem found.
        """
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object ({}).")

        for key in ("aeropuertos", "rutas"):
            if key not in data:
                raise ValueError(f"Missing required top-level key: '{key}'.")
            if not isinstance(data[key], list):
                raise ValueError(f"Top-level key '{key}' must be a list.")

        for i, node in enumerate(data["aeropuertos"]):
            missing = _REQUIRED_NODE_FIELDS - set(node.keys())
            if missing:
                raise ValueError(
                    f"Airport at index {i} (id='{node.get('id', '?')}') "
                    f"is missing required fields: {sorted(missing)}."
                )

        for i, edge in enumerate(data["rutas"]):
            missing = _REQUIRED_EDGE_FIELDS - set(edge.keys())
            if missing:
                raise ValueError(
                    f"Route at index {i} "
                    f"({edge.get('origen','?')} → {edge.get('destino','?')}) "
                    f"is missing required fields: {sorted(missing)}."
                )

    # ------------------------------------------------------------------
    # Config builder
    # ------------------------------------------------------------------

    def _build_config(self, raw: dict) -> dict:
        """
        Merge the JSON config section with built-in defaults.

        The JSON can override:
          * Individual aircraft costoKm / tiempoKm values.
          * presupuestoMinimoPorc (default 35 %).
          * intervaloAlojamiento  (default 20 hours).
          * intervaloAlimentacion (default 8 hours).
        """
        config: dict[str, Any] = {
            "presupuestoMinimoPorc":    raw.get("presupuestoMinimoPorc", 35),
            "maxSubsidiadaPorcentaje":  raw.get("maxSubsidiadaPorcentaje", 20),
            "intervaloAlojamiento":     raw.get("intervaloAlojamiento", 20),
            "intervaloAlimentacion":    raw.get("intervaloAlimentacion", 8),
            "aeronaves": {},
        }
        raw_aircraft: dict = raw.get("aeronaves", {})
        for nombre, defaults in DEFAULT_AIRCRAFT.items():
            override = raw_aircraft.get(nombre, {})
            config["aeronaves"][nombre] = {
                "costo_km":  override.get("costoKm",  defaults["costo_km"]),
                "tiempo_km": override.get("tiempoKm", defaults["tiempo_km"]),
            }
        return config

    # ------------------------------------------------------------------
    # Object builders
    # ------------------------------------------------------------------

    def _build_aircraft_registry(self, config: dict) -> dict[str, Aircraft]:
        """Build an Aircraft object for each type using the resolved config."""
        return {
            nombre: Aircraft(
                nombre=nombre,
                costo_km=rates["costo_km"],
                tiempo_km=rates["tiempo_km"],
            )
            for nombre, rates in config["aeronaves"].items()
        }

    def _build_airport(self, data: dict) -> Airport:
        """Build an Airport from a raw JSON node dict."""
        actividades = [self._build_activity(a) for a in data.get("actividades", [])]
        trabajos    = [self._build_job(j)      for j in data.get("trabajos",    [])]
        return Airport(
            id=str(data["id"]).upper(),
            nombre=data["nombre"],
            ciudad=data["ciudad"],
            pais=data["pais"],
            zona_horaria=data["zonaHoraria"],
            es_hub=bool(data["esHub"]),
            costo_alojamiento=float(data["costoAlojamiento"]),
            costo_alimentacion=float(data["costoAlimentacion"]),
            actividades=actividades,
            trabajos=trabajos,
            aerolineas=data.get("aerolineas", []),
        )

    def _build_route(self, data: dict, aircraft_registry: dict[str, Aircraft]) -> Route:
        """Build a Route from a raw JSON edge dict."""
        aeronaves: list[str] = data["aeronaves"]
        for nombre in aeronaves:
            if nombre not in aircraft_registry:
                raise ValueError(
                    f"Unknown aircraft type '{nombre}' in route "
                    f"{data.get('origen','?')} → {data.get('destino','?')}. "
                    f"Valid types: {list(aircraft_registry.keys())}."
                )
        return Route(
            origen=str(data["origen"]).upper(),
            destino=str(data["destino"]).upper(),
            distancia_km=float(data["distanciaKm"]),
            aeronaves=aeronaves,
            costo_base=float(data.get("costoBase", 0.0)),
            estancia_minima=int(data.get("estanciaMinima", 60)),
        )

    def _build_activity(self, data: dict) -> Activity:
        """Build an Activity from a raw JSON activity dict."""
        return Activity(
            nombre=data["nombre"],
            tipo=data.get("tipo", Activity.TIPO_OPCIONAL),
            duracion_min=int(data["duracionMin"]),
            costo_usd=float(data["costoUSD"]),
        )

    def _build_job(self, data: dict) -> Job:
        """Build a Job from a raw JSON job dict."""
        return Job(
            nombre=data["nombre"],
            tarifa_hora=float(data["tarifaHora"]),
            max_horas=int(data["maxHoras"]),
        )

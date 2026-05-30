from __future__ import annotations


class Airport:
    """
    Represents an airport node in the flight network graph.

    Each airport is uniquely identified by its IATA code (e.g. 'BOG', 'LIM').
    Hub airports differ from secondary ones visually in the UI and may be
    excluded from route calculations when the traveler opts to skip secondary
    airports.

    Attributes:
        id                 : IATA code (3 letters, uppercase).
        nombre             : Full airport name.
        ciudad             : City name.
        pais               : Country name.
        zona_horaria       : Timezone string (e.g. 'America/Bogota').
        es_hub             : True when the airport is a major hub.
        costo_alojamiento  : Accommodation cost per night in USD.
        costo_alimentacion : Meal cost per sitting in USD.
        actividades        : List of Activity objects available at this airport.
        trabajos           : List of Job objects available at this airport.
        aerolineas         : Airlines that operate from this airport.
    """

    def __init__(
        self,
        id: str,
        nombre: str,
        ciudad: str,
        pais: str,
        zona_horaria: str,
        es_hub: bool,
        costo_alojamiento: float,
        costo_alimentacion: float,
        actividades: list | None = None,
        trabajos: list | None = None,
        aerolineas: list[str] | None = None,
    ) -> None:
        self.id = id
        self.nombre = nombre
        self.ciudad = ciudad
        self.pais = pais
        self.zona_horaria = zona_horaria
        self.es_hub = es_hub
        self.costo_alojamiento = costo_alojamiento
        self.costo_alimentacion = costo_alimentacion
        self.actividades: list = actividades or []
        self.trabajos: list = trabajos or []
        self.aerolineas: list[str] = aerolineas or []

    def __repr__(self) -> str:
        hub_label = " [HUB]" if self.es_hub else ""
        return f"Airport({self.id}{hub_label}, {self.ciudad}, {self.pais})"

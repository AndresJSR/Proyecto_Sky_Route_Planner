# Default rates for every aircraft type as specified in the project requirements.
# These values can be overridden per-route via the JSON config section.
DEFAULT_AIRCRAFT: dict[str, dict[str, float]] = {
    "Avión Comercial": {"costo_km": 0.18, "tiempo_km": 0.7},
    "Avión Regional":  {"costo_km": 0.25, "tiempo_km": 1.1},
    "Hélice":          {"costo_km": 0.12, "tiempo_km": 2.5},
}


class Aircraft:
    """
    Represents an aircraft type with its cost and flight-time rates per km.

    Cost formula  : distancia_km * costo_km  → USD
    Time formula  : distancia_km * tiempo_km → minutes

    Default values (from project spec):
        Avión Comercial : $0.18/km, 0.7 min/km
        Avión Regional  : $0.25/km, 1.1 min/km
        Hélice          : $0.12/km, 2.5 min/km

    These defaults can be overridden through the global config section of the
    JSON file, which allows the UI to persist custom aircraft rates.

    Attributes:
        nombre   : Aircraft type name.
        costo_km : Cost per km in USD.
        tiempo_km: Flight time per km in minutes.
    """

    def __init__(self, nombre: str, costo_km: float, tiempo_km: float) -> None:
        self.nombre = nombre
        self.costo_km = costo_km
        self.tiempo_km = tiempo_km

    def calcular_costo(self, distancia_km: float) -> float:
        """Calculate total flight cost in USD for a given distance."""
        return round(distancia_km * self.costo_km, 2)

    def calcular_tiempo(self, distancia_km: float) -> float:
        """Calculate total flight time in minutes for a given distance."""
        return round(distancia_km * self.tiempo_km, 2)

    @classmethod
    def from_defaults(cls, nombre: str) -> "Aircraft":
        """
        Build an Aircraft instance using the built-in default rates.

        Args:
            nombre: Aircraft type name. Must be a key in DEFAULT_AIRCRAFT.

        Raises:
            ValueError: If the aircraft type is not recognised.
        """
        if nombre not in DEFAULT_AIRCRAFT:
            raise ValueError(
                f"Unknown aircraft type '{nombre}'. "
                f"Valid types: {list(DEFAULT_AIRCRAFT.keys())}"
            )
        data = DEFAULT_AIRCRAFT[nombre]
        return cls(nombre=nombre, costo_km=data["costo_km"], tiempo_km=data["tiempo_km"])

    def __repr__(self) -> str:
        return (
            f"Aircraft(nombre='{self.nombre}', "
            f"costo=${self.costo_km}/km, tiempo={self.tiempo_km} min/km)"
        )

class Route:
    """
    Represents a directed weighted edge in the flight network graph.

    The graph is directed: if route A→B exists, B→A must be declared
    explicitly in the JSON. There is no implicit reverse edge.

    The 'bloqueada' flag is set by the interruption service to simulate
    airspace closures, adverse weather, or airline cancellations. Blocked
    routes remain in the adjacency list but are excluded from all path
    searches (see AdjacencyGraph.get_neighbors).

    Subsidised routes (costoBase == 0) have free flight cost. The traveler
    cannot use subsidised routes for more than 20 % of the total trip distance.

    Attributes:
        origen          : IATA code of the origin airport.
        destino         : IATA code of the destination airport.
        distancia_km    : Distance of the leg in kilometres.
        aeronaves       : Aircraft type names available on this route.
        costo_base      : Override cost; 0 means the route is subsidised.
        estancia_minima : Minimum stay at the destination in minutes.
        bloqueada       : True when the route is currently interrupted.
    """

    def __init__(
        self,
        origen: str,
        destino: str,
        distancia_km: float,
        aeronaves: list[str],
        costo_base: float = 0.0,
        estancia_minima: int = 60,
    ) -> None:
        self.origen = origen
        self.destino = destino
        self.distancia_km = distancia_km
        self.aeronaves = aeronaves
        self.costo_base = costo_base
        self.estancia_minima = estancia_minima
        self.bloqueada: bool = False

    @property
    def es_subsidiada(self) -> bool:
        """True when this is a subsidised (zero-cost) route."""
        return self.costo_base == 0.0

    def bloquear(self) -> None:
        """Block this route, simulating an interruption event."""
        self.bloqueada = True

    def desbloquear(self) -> None:
        """Restore a previously blocked route."""
        self.bloqueada = False

    def __repr__(self) -> str:
        estado = " [BLOQUEADA]" if self.bloqueada else ""
        sub = " [SUBSIDIADA]" if self.es_subsidiada else ""
        return (
            f"Route({self.origen} → {self.destino}, "
            f"{self.distancia_km} km{sub}{estado})"
        )

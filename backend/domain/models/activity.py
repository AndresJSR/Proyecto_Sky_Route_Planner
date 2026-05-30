class Activity:
    """
    Represents an optional activity available at an airport node.

    Optional activities are offered to the traveler at each destination:
    tours, museum visits, cultural activities, etc.

    Mandatory activities (accommodation and meals) are NOT modeled here;
    their costs live directly on the Airport node and are handled by the
    advanced planner service according to the elapsed time rules.

    Attributes:
        nombre      : Activity name.
        tipo        : 'obligatoria' or 'opcional'.
        duracion_min: Duration in minutes.
        costo_usd   : Cost in USD.
    """

    TIPO_OBLIGATORIA = "obligatoria"
    TIPO_OPCIONAL = "opcional"

    def __init__(
        self,
        nombre: str,
        tipo: str,
        duracion_min: int,
        costo_usd: float,
    ) -> None:
        if tipo not in (self.TIPO_OBLIGATORIA, self.TIPO_OPCIONAL):
            raise ValueError(
                f"Invalid activity type '{tipo}'. "
                f"Use '{self.TIPO_OBLIGATORIA}' or '{self.TIPO_OPCIONAL}'."
            )
        self.nombre = nombre
        self.tipo = tipo
        self.duracion_min = duracion_min
        self.costo_usd = costo_usd

    @property
    def es_obligatoria(self) -> bool:
        """Return True when this activity is mandatory."""
        return self.tipo == self.TIPO_OBLIGATORIA

    def __repr__(self) -> str:
        return (
            f"Activity(nombre='{self.nombre}', tipo='{self.tipo}', "
            f"duracion={self.duracion_min} min, costo=${self.costo_usd})"
        )

class Job:
    """
    Represents a temporary job available at an airport.

    The traveler may accept a job when their current budget falls below
    35 % of the initial budget (threshold configurable in the JSON).

    Income formula: tarifa_hora * min(horas_solicitadas, max_horas).

    Attributes:
        nombre     : Job name (e.g. 'Cargador de equipaje').
        tarifa_hora: Hourly pay rate in USD.
        max_horas  : Maximum hours the traveler can work in this job.
    """

    def __init__(self, nombre: str, tarifa_hora: float, max_horas: int) -> None:
        self.nombre = nombre
        self.tarifa_hora = tarifa_hora
        self.max_horas = max_horas

    def calcular_ingreso(self, horas: float) -> float:
        """
        Calculate income for the given hours, capped by max_horas.

        Args:
            horas: Hours the traveler wants to work.

        Returns:
            Total income in USD, rounded to 2 decimal places.
        """
        horas_efectivas = min(float(horas), float(self.max_horas))
        return round(horas_efectivas * self.tarifa_hora, 2)

    def __repr__(self) -> str:
        return (
            f"Job(nombre='{self.nombre}', "
            f"tarifa=${self.tarifa_hora}/h, max={self.max_horas}h)"
        )

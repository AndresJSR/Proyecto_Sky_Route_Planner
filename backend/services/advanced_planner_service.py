# Stub for Persona 3 — Advanced planner (step-by-step traveler simulation)
# TODO: Implement dynamic budget management, jobs, activities, meal/lodging logic
from graph.adjacency_graph import AdjacencyGraph


class AdvancedPlannerService:
    """Step-by-step traveler simulation with dynamic budget and activities."""

    def __init__(self, graph: AdjacencyGraph, config: dict) -> None:
        self.graph = graph
        self.config = config

    def iniciar_viaje(self, origen: str, presupuesto_inicial: float) -> dict:
        """Initialise traveler state at the origin airport."""
        raise NotImplementedError

    def avanzar_paso(self, estado: dict, destino: str, aeronave: str) -> dict:
        """Move the traveler one leg forward and apply mandatory costs."""
        raise NotImplementedError

    def realizar_actividad(self, estado: dict, actividad_nombre: str) -> dict:
        """Apply an optional activity at the current airport."""
        raise NotImplementedError

    def tomar_trabajo(self, estado: dict, trabajo_nombre: str, horas: float) -> dict:
        """Have the traveler work at the current airport to earn income."""
        raise NotImplementedError

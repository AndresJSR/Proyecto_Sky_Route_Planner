"""
Tests for domain model classes (Persona 1 — R1).

Covers: Airport, Route, Aircraft, Activity, Job
"""

import pytest

from domain.models.activity import Activity
from domain.models.aircraft import Aircraft, DEFAULT_AIRCRAFT
from domain.models.airport import Airport
from domain.models.job import Job
from domain.models.route import Route


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def airport_hub():
    return Airport(
        id="BOG",
        nombre="Aeropuerto El Dorado",
        ciudad="Bogotá",
        pais="Colombia",
        zona_horaria="America/Bogota",
        es_hub=True,
        costo_alojamiento=60.0,
        costo_alimentacion=12.0,
    )


@pytest.fixture
def airport_secondary():
    return Airport(
        id="CTG",
        nombre="Aeropuerto Rafael Núñez",
        ciudad="Cartagena",
        pais="Colombia",
        zona_horaria="America/Bogota",
        es_hub=False,
        costo_alojamiento=70.0,
        costo_alimentacion=14.0,
    )


@pytest.fixture
def route_normal():
    return Route(
        origen="BOG",
        destino="CTG",
        distancia_km=730.0,
        aeronaves=["Avión Comercial"],
        costo_base=1.0,
        estancia_minima=90,
    )


@pytest.fixture
def route_subsidized():
    return Route(
        origen="CLO",
        destino="GYE",
        distancia_km=600.0,
        aeronaves=["Avión Regional", "Hélice"],
        costo_base=0.0,
        estancia_minima=60,
    )


# ──────────────────────────────────────────────
# Airport tests
# ──────────────────────────────────────────────

class TestAirport:
    def test_attributes_stored(self, airport_hub):
        assert airport_hub.id == "BOG"
        assert airport_hub.ciudad == "Bogotá"
        assert airport_hub.pais == "Colombia"
        assert airport_hub.zona_horaria == "America/Bogota"
        assert airport_hub.costo_alojamiento == 60.0
        assert airport_hub.costo_alimentacion == 12.0

    def test_hub_flag_true(self, airport_hub):
        assert airport_hub.es_hub is True

    def test_hub_flag_false(self, airport_secondary):
        assert airport_secondary.es_hub is False

    def test_default_empty_lists(self, airport_hub):
        assert airport_hub.actividades == []
        assert airport_hub.trabajos == []
        assert airport_hub.aerolineas == []

    def test_activities_and_jobs_stored(self):
        act = Activity("Tour", Activity.TIPO_OPCIONAL, 120, 10.0)
        job = Job("Cargador", 6.0, 8)
        a = Airport(
            id="MDE", nombre="José María Córdova", ciudad="Medellín",
            pais="Colombia", zona_horaria="America/Bogota",
            es_hub=True, costo_alojamiento=55.0, costo_alimentacion=10.0,
            actividades=[act], trabajos=[job], aerolineas=["Avianca"],
        )
        assert len(a.actividades) == 1
        assert len(a.trabajos) == 1
        assert a.aerolineas == ["Avianca"]

    def test_repr_contains_id(self, airport_hub):
        assert "BOG" in repr(airport_hub)

    def test_repr_marks_hub(self, airport_hub):
        assert "HUB" in repr(airport_hub)

    def test_repr_no_hub_label_on_secondary(self, airport_secondary):
        assert "HUB" not in repr(airport_secondary)


# ──────────────────────────────────────────────
# Route tests
# ──────────────────────────────────────────────

class TestRoute:
    def test_attributes_stored(self, route_normal):
        assert route_normal.origen == "BOG"
        assert route_normal.destino == "CTG"
        assert route_normal.distancia_km == 730.0
        assert route_normal.aeronaves == ["Avión Comercial"]
        assert route_normal.estancia_minima == 90

    def test_not_blocked_by_default(self, route_normal):
        assert route_normal.bloqueada is False

    def test_not_subsidized_when_costo_base_nonzero(self, route_normal):
        assert route_normal.es_subsidiada is False

    def test_subsidized_when_costo_base_zero(self, route_subsidized):
        assert route_subsidized.es_subsidiada is True

    def test_bloquear_sets_flag(self, route_normal):
        route_normal.bloquear()
        assert route_normal.bloqueada is True

    def test_desbloquear_clears_flag(self, route_normal):
        route_normal.bloquear()
        route_normal.desbloquear()
        assert route_normal.bloqueada is False

    def test_repr_shows_blocked_label(self, route_normal):
        route_normal.bloquear()
        assert "BLOQUEADA" in repr(route_normal)

    def test_repr_shows_subsidized_label(self, route_subsidized):
        assert "SUBSIDIADA" in repr(route_subsidized)

    def test_repr_shows_arrow(self, route_normal):
        assert "BOG" in repr(route_normal)
        assert "CTG" in repr(route_normal)


# ──────────────────────────────────────────────
# Aircraft tests
# ──────────────────────────────────────────────

class TestAircraft:
    @pytest.mark.parametrize("nombre", list(DEFAULT_AIRCRAFT.keys()))
    def test_from_defaults_creates_instance(self, nombre):
        a = Aircraft.from_defaults(nombre)
        assert a.nombre == nombre
        assert a.costo_km == DEFAULT_AIRCRAFT[nombre]["costo_km"]
        assert a.tiempo_km == DEFAULT_AIRCRAFT[nombre]["tiempo_km"]

    def test_from_defaults_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown aircraft type"):
            Aircraft.from_defaults("Boeing 999")

    def test_calcular_costo(self):
        a = Aircraft.from_defaults("Avión Comercial")
        assert a.calcular_costo(1000.0) == round(1000.0 * 0.18, 2)

    def test_calcular_tiempo(self):
        a = Aircraft.from_defaults("Avión Comercial")
        assert a.calcular_tiempo(1000.0) == round(1000.0 * 0.7, 2)

    def test_custom_rates(self):
        a = Aircraft(nombre="Custom", costo_km=0.50, tiempo_km=1.0)
        assert a.calcular_costo(200.0) == 100.0
        assert a.calcular_tiempo(200.0) == 200.0

    def test_default_rates_values(self):
        comercial = Aircraft.from_defaults("Avión Comercial")
        regional  = Aircraft.from_defaults("Avión Regional")
        helice    = Aircraft.from_defaults("Hélice")
        assert comercial.costo_km == 0.18
        assert regional.costo_km  == 0.25
        assert helice.costo_km    == 0.12
        assert comercial.tiempo_km == 0.7
        assert regional.tiempo_km  == 1.1
        assert helice.tiempo_km    == 2.5

    def test_repr_contains_name(self):
        a = Aircraft.from_defaults("Hélice")
        assert "Hélice" in repr(a)


# ──────────────────────────────────────────────
# Activity tests
# ──────────────────────────────────────────────

class TestActivity:
    def test_optional_activity(self):
        a = Activity("Tour", Activity.TIPO_OPCIONAL, 120, 15.0)
        assert a.nombre == "Tour"
        assert a.tipo == Activity.TIPO_OPCIONAL
        assert a.duracion_min == 120
        assert a.costo_usd == 15.0
        assert a.es_obligatoria is False

    def test_mandatory_activity(self):
        a = Activity("Alojamiento", Activity.TIPO_OBLIGATORIA, 480, 60.0)
        assert a.es_obligatoria is True

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid activity type"):
            Activity("X", "invalido", 60, 0.0)

    def test_zero_cost_activity(self):
        a = Activity("Plaza libre", Activity.TIPO_OPCIONAL, 60, 0.0)
        assert a.costo_usd == 0.0

    def test_repr_contains_name(self):
        a = Activity("Museo", Activity.TIPO_OPCIONAL, 90, 8.0)
        assert "Museo" in repr(a)


# ──────────────────────────────────────────────
# Job tests
# ──────────────────────────────────────────────

class TestJob:
    def test_attributes_stored(self):
        j = Job("Cargador de equipaje", 6.0, 8)
        assert j.nombre == "Cargador de equipaje"
        assert j.tarifa_hora == 6.0
        assert j.max_horas == 8

    def test_calcular_ingreso_normal(self):
        j = Job("Asistente", 8.0, 6)
        assert j.calcular_ingreso(4) == 32.0

    def test_calcular_ingreso_capped_at_max(self):
        j = Job("Guía", 10.0, 5)
        assert j.calcular_ingreso(10) == 50.0  # capped at 5 hours

    def test_calcular_ingreso_fractional_hours(self):
        j = Job("Guía", 10.0, 8)
        assert j.calcular_ingreso(2.5) == 25.0

    def test_calcular_ingreso_zero_hours(self):
        j = Job("Guía", 10.0, 8)
        assert j.calcular_ingreso(0) == 0.0

    def test_repr_contains_name(self):
        j = Job("Cargador", 6.0, 8)
        assert "Cargador" in repr(j)

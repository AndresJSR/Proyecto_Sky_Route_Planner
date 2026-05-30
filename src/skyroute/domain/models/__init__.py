"""Domain models."""

from .activity import Activity
from .activity_record import ActivityRecord
from .aircraft import Aircraft
from .airport import Airport
from .flight_segment import FlightSegment
from .itinerary import Itinerary
from .job import Job
from .job_record import JobRecord
from .route import Route
from .traveler_state import TravelerState
from .visited_destination import VisitedDestination

__all__ = [
    "Activity",
    "ActivityRecord",
    "Aircraft",
    "Airport",
    "FlightSegment",
    "Itinerary",
    "Job",
    "JobRecord",
    "Route",
    "TravelerState",
    "VisitedDestination",
]

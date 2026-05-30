"""Job record domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .job import Job


@dataclass(slots=True)
class JobRecord:
    """Stores the execution state of a job."""

    job_id: str
    job: Job | None = None
    completed_at: datetime | None = None
    notes: str | None = None

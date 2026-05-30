"""Job domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Job:
    """Represents a travel-related task or objective."""

    id: str
    title: str
    description: str | None = None
    required_budget_usd: float | None = None

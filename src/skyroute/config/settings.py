"""Application settings for SkyRoute Planner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Top-level application settings placeholder."""

    application_name: str = "SkyRoute Planner"
    data_directory: str = "data"
    sample_airports_file: str = "data/sample_airports.json"
    debug: bool = False

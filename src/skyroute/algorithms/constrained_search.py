"""Constrained search placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from ..graph import AirRouteGraph


@dataclass(slots=True)
class ConstrainedSearch:
    """Skeleton for path search under user-defined constraints."""

    graph: AirRouteGraph

    def search(self, origin_code: str, destination_code: str) -> list[str]:
        """Search a route using constraints.

        TODO: Add constraint handling for budget, activities, and time windows.
        """
        raise NotImplementedError("ConstrainedSearch.search is not implemented yet.")

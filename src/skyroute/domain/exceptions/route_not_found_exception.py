"""Exception raised when a requested route is not available."""

from __future__ import annotations

from .graph_exception import GraphException


class RouteNotFoundException(GraphException):
    """Raised when a route cannot be found in the graph."""

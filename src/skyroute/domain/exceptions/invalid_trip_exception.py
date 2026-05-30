"""Exception raised when trip constraints are invalid."""

from __future__ import annotations

from .graph_exception import GraphException


class InvalidTripException(GraphException):
    """Raised when a trip cannot be planned with the provided constraints."""

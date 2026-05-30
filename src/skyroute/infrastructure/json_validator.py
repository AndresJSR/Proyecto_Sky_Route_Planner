"""JSON payload validation utilities."""

from __future__ import annotations


class JsonValidator:
    """Validates the structure of graph JSON payloads."""

    def validate_graph_payload(self, payload: dict[str, object]) -> None:
        """Validate the top-level graph payload.

        TODO: Add stricter validation rules as the JSON contract evolves.
        """
        if not isinstance(payload, dict):
            raise ValueError("Graph payload must be a dictionary.")
        if "airports" not in payload:
            raise ValueError("Graph payload must include an 'airports' section.")
        if "routes" not in payload:
            raise ValueError("Graph payload must include a 'routes' section.")

"""
SkyRoute Planner — Backend entry point.

Run API server:
    python main.py

Run network check:
    python main.py --check

This file starts the FastAPI backend so the frontend can consume all graph
and basic planning routes. It also keeps a small network check mode for
debugging the JSON loader and graph construction.
"""

from __future__ import annotations

import os
import sys

import uvicorn

# Ensure the backend root is on the Python path when run directly.
BACKEND_DIR = os.path.dirname(__file__)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from infrastructure.json_loader import JSONLoader


DATA_FILE = os.path.join(BACKEND_DIR, "data", "network.json")


def check_network() -> None:
    """
    Load the network JSON and print a quick graph summary.
    """
    loader = JSONLoader()
    graph, config = loader.load(DATA_FILE)

    print("=== SkyRoute Planner — Network Loaded ===")
    print(graph)
    print(f"  Hubs               : {[a.id for a in graph.get_hubs()]}")
    print(f"  Secondary airports : {len(graph.get_secondary_airports())}")
    print(f"  Routes             : {graph.edge_count()}")
    print(f"  Config             : {config}")


def run_api() -> None:
    """
    Start the SkyRoute Planner API server.
    """
    uvicorn.run(
        "interfaces.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


def main() -> None:
    """
    Main execution dispatcher.

    Default behavior:
        Start the API server.

    Optional:
        Use --check to validate that the graph loads correctly.
    """
    if "--check" in sys.argv:
        check_network()
        return

    run_api()


if __name__ == "__main__":
    main()
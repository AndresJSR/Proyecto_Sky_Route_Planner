"""
SkyRoute Planner — Backend entry point.

Run with:
    python main.py

This script loads the flight network from data/network.json and verifies
that the graph is correctly built. All other functionality is exposed
through the services layer and (eventually) the REST API.
"""

import os
import sys

# Ensure the backend root is on the Python path when run directly.
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.json_loader import JSONLoader


DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "network.json")


def main() -> None:
    loader = JSONLoader()
    graph, config = loader.load(DATA_FILE)

    print("=== SkyRoute Planner — Network Loaded ===")
    print(graph)
    print(f"  Hubs            : {[a.id for a in graph.get_hubs()]}")
    print(f"  Secondary airports: {len(graph.get_secondary_airports())}")
    print(f"  Config          : {config}")


if __name__ == "__main__":
    main()

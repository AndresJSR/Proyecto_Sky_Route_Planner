.
├── backend
│   ├── algorithms
│   │   ├── backtracking.py
│   │   ├── dijkstra.py
│   │   ├── __init__.py
│   │   └── shared.py
│   ├── check_controller.py
│   ├── data
│   │   └── network.json
│   ├── domain
│   │   ├── __init__.py
│   │   └── models
│   │       ├── activity.py
│   │       ├── aircraft.py
│   │       ├── airport.py
│   │       ├── __init__.py
│   │       ├── job.py
│   │       └── route.py
│   ├── graph
│   │   ├── adjacency_graph.py
│   │   └── __init__.py
│   ├── infrastructure
│   │   ├── __init__.py
│   │   └── json_loader.py
│   ├── interfaces
│   │   ├── api
│   │   │   ├── advanced_planner_controller.py
│   │   │   ├── app.py
│   │   │   ├── graph_controller.py
│   │   │   ├── __init__.py
│   │   │   ├── interruption_controller.py
│   │   │   ├── planner_controller.py
│   │   │   └── report_controller.py
│   │   └── __init__.py
│   ├── main.py
│   ├── pytest.ini
│   ├── services
│   │   ├── advanced_planner_service.py
│   │   ├── basic_planner_service.py
│   │   ├── graph_service.py
│   │   ├── __init__.py
│   │   ├── interruption_service.py
│   │   └── report_service.py
│   ├── test_planner.py
│   └── tests
│       ├── __init__.py
│       ├── test_adjacency_graph.py
│       ├── test_advanced_planner_r3.py
│       ├── test_backtracking.py
│       ├── test_basic_planner.py
│       ├── test_dijkstra.py
│       ├── test_graph_controller.py
│       ├── test_in_transit_r4.py
│       ├── test_json_loader.py
│       ├── test_models.py
│       ├── test_planner_controller.py
│       ├── test_report_r5.py
│       ├── test_require_all_transport_types.py
│       ├── test_route_options_r2.py
│       └── test_shared.py
├── README.md
└── requirements.txt

11 directories, 51 files

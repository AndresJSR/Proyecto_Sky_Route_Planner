.
├── data
│   └── sample_airports.json
├── README.md
├── requirements.txt
├── src
│   └── skyroute
│       ├── algorithms
│       │   ├── constrained_search.py
│       │   ├── dijkstra.py
│       │   ├── __init__.py
│       │   ├── __pycache__
│       │   │   ├── constrained_search.cpython-310.pyc
│       │   │   ├── dijkstra.cpython-310.pyc
│       │   │   ├── __init__.cpython-310.pyc
│       │   │   └── route_optimizer.cpython-310.pyc
│       │   └── route_optimizer.py
│       ├── application
│       │   ├── __init__.py
│       │   ├── __pycache__
│       │   │   └── __init__.cpython-310.pyc
│       │   └── services
│       │       ├── advanced_planner_service.py
│       │       ├── basic_planner_service.py
│       │       ├── graph_service.py
│       │       ├── __init__.py
│       │       ├── interruption_service.py
│       │       ├── __pycache__
│       │       │   ├── advanced_planner_service.cpython-310.pyc
│       │       │   ├── basic_planner_service.cpython-310.pyc
│       │       │   ├── graph_service.cpython-310.pyc
│       │       │   ├── __init__.cpython-310.pyc
│       │       │   ├── interruption_service.cpython-310.pyc
│       │       │   └── report_service.cpython-310.pyc
│       │       └── report_service.py
│       ├── config
│       │   ├── default_aircraft_config.py
│       │   ├── __init__.py
│       │   ├── __pycache__
│       │   │   ├── default_aircraft_config.cpython-310.pyc
│       │   │   ├── __init__.cpython-310.pyc
│       │   │   └── settings.cpython-310.pyc
│       │   └── settings.py
│       ├── domain
│       │   ├── enums
│       │   │   ├── activity_type.py
│       │   │   ├── aircraft_type.py
│       │   │   ├── __init__.py
│       │   │   ├── optimization_criterion.py
│       │   │   └── __pycache__
│       │   │       ├── activity_type.cpython-310.pyc
│       │   │       ├── aircraft_type.cpython-310.pyc
│       │   │       ├── __init__.cpython-310.pyc
│       │   │       └── optimization_criterion.cpython-310.pyc
│       │   ├── exceptions
│       │   │   ├── graph_exception.py
│       │   │   ├── __init__.py
│       │   │   ├── invalid_trip_exception.py
│       │   │   ├── __pycache__
│       │   │   │   ├── graph_exception.cpython-310.pyc
│       │   │   │   ├── __init__.cpython-310.pyc
│       │   │   │   ├── invalid_trip_exception.cpython-310.pyc
│       │   │   │   └── route_not_found_exception.cpython-310.pyc
│       │   │   └── route_not_found_exception.py
│       │   ├── __init__.py
│       │   ├── models
│       │   │   ├── activity.py
│       │   │   ├── activity_record.py
│       │   │   ├── aircraft.py
│       │   │   ├── airport.py
│       │   │   ├── flight_segment.py
│       │   │   ├── __init__.py
│       │   │   ├── itinerary.py
│       │   │   ├── job.py
│       │   │   ├── job_record.py
│       │   │   ├── __pycache__
│       │   │   │   ├── activity.cpython-310.pyc
│       │   │   │   ├── activity_record.cpython-310.pyc
│       │   │   │   ├── aircraft.cpython-310.pyc
│       │   │   │   ├── airport.cpython-310.pyc
│       │   │   │   ├── flight_segment.cpython-310.pyc
│       │   │   │   ├── __init__.cpython-310.pyc
│       │   │   │   ├── itinerary.cpython-310.pyc
│       │   │   │   ├── job.cpython-310.pyc
│       │   │   │   ├── job_record.cpython-310.pyc
│       │   │   │   ├── route.cpython-310.pyc
│       │   │   │   ├── traveler_state.cpython-310.pyc
│       │   │   │   └── visited_destination.cpython-310.pyc
│       │   │   ├── route.py
│       │   │   ├── traveler_state.py
│       │   │   └── visited_destination.py
│       │   └── __pycache__
│       │       └── __init__.cpython-310.pyc
│       ├── graph
│       │   ├── adjacency_list.py
│       │   ├── air_route_graph.py
│       │   ├── __init__.py
│       │   └── __pycache__
│       │       ├── adjacency_list.cpython-310.pyc
│       │       ├── air_route_graph.cpython-310.pyc
│       │       └── __init__.cpython-310.pyc
│       ├── infrastructure
│       │   ├── __init__.py
│       │   ├── json_loader.py
│       │   ├── json_validator.py
│       │   └── __pycache__
│       │       ├── __init__.cpython-310.pyc
│       │       ├── json_loader.cpython-310.pyc
│       │       └── json_validator.cpython-310.pyc
│       ├── __init__.py
│       ├── interfaces
│       │   ├── api
│       │   │   ├── controllers
│       │   │   │   ├── graph_controller.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── planner_controller.py
│       │   │   │   ├── __pycache__
│       │   │   │   │   ├── graph_controller.cpython-310.pyc
│       │   │   │   │   ├── __init__.cpython-310.pyc
│       │   │   │   │   ├── planner_controller.cpython-310.pyc
│       │   │   │   │   ├── report_controller.cpython-310.pyc
│       │   │   │   │   └── trip_controller.cpython-310.pyc
│       │   │   │   ├── report_controller.py
│       │   │   │   └── trip_controller.py
│       │   │   ├── __init__.py
│       │   │   ├── __pycache__
│       │   │   │   └── __init__.cpython-310.pyc
│       │   │   └── schemas
│       │   │       ├── graph_schema.py
│       │   │       ├── __init__.py
│       │   │       ├── planner_schema.py
│       │   │       ├── __pycache__
│       │   │       │   ├── graph_schema.cpython-310.pyc
│       │   │       │   ├── __init__.cpython-310.pyc
│       │   │       │   ├── planner_schema.cpython-310.pyc
│       │   │       │   └── trip_schema.cpython-310.pyc
│       │   │       └── trip_schema.py
│       │   ├── __init__.py
│       │   └── __pycache__
│       │       └── __init__.cpython-310.pyc
│       ├── main.py
│       ├── __pycache__
│       │   ├── __init__.cpython-310.pyc
│       │   └── main.cpython-310.pyc
│       └── utils
│           ├── constants.py
│           ├── __init__.py
│           ├── __pycache__
│           │   ├── constants.cpython-310.pyc
│           │   ├── __init__.cpython-310.pyc
│           │   └── time_utils.cpython-310.pyc
│           └── time_utils.py
└── tests
    ├── __init__.py
    ├── __pycache__
    │   ├── __init__.cpython-310.pyc
    │   ├── test_basic_planner.cpython-310.pyc
    │   ├── test_dijkstra.cpython-310.pyc
    │   ├── test_graph.cpython-310.pyc
    │   └── test_json_loader.cpython-310.pyc
    ├── test_basic_planner.py
    ├── test_dijkstra.py
    ├── test_graph.py
    └── test_json_loader.py

36 directories, 127 files

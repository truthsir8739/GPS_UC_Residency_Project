# GPS Navigation System

## Overview

The GPS Navigation System is a Python-based application designed to provide real-time navigation around the University of Kentucky campus in Lexington, KY. It leverages OpenStreetMap (OSM) data through the osmnx library to create a detailed street network and uses Dijkstra's algorithm to compute optimal routes.

The system supports two modes:

- Normal Mode for the fastest route and Learner Mode for safer routes with additional guidance, such as safety tips and blind spot alerts.

This project is ideal for users seeking a customizable navigation tool that integrates real-world map data with enhanced features like landmark-based directions and crowd-aware routing.

### Features

- Route Planning: Computes the fastest or safest routes between two points using coordinates or addresses.
- Learner Mode: Provides safer routes with crowd-level adjustments, blind spot warnings, and driving tips tailored for new drivers.
- Landmark Integration: Includes nearby landmarks (e.g., Memorial Coliseum, William T. Young Library) to enhance navigation context.
- Geocoding: Converts addresses to coordinates using the Nominatim geocoding service.
- Interactive CLI: User-friendly command-line interface to input start/end points and select navigation modes.
- Comprehensive Summaries: Displays route details, including distance, estimated travel time, number of turns, and step-by-step directions.

### Project Structure

```text
.
├── pyproject.toml # Project configuration and dependencies
├── README.md
└── residency # Main application directory
    ├── __init__.py
    ├── graph.py # Graph class with Dijkstra's algorithm
    ├── main.py # Main script to run the navigation system
    ├── navigation.py # EnhancedRealWorldGPS class for map loading and routing
    ├── screenshots
    │   └── gps_navigation_tests_passing.png
    └── tests  # Test suite
        ├── __init__.py
        └── test_graph.py # Unit tests for GPS functionality

```

### Installation

- Clone the Repository
- Set Up a Virtual Environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

- Install Dependencies: Ensure you have Python 3.8+ installed.
- Install the required packages using the pyproject.toml file:

```bash
pip install --editable ".[dev]"
```

This installs dependencies like osmnx, networkx, geopy, and others specified in pyproject.toml.

- Verify Installation: Run the main script to ensure the system is set up correctly:

```bash
python residency/main.py
```

### Usage

- Run the Application:

```bash
python residency/main.py
```

- Follow the Prompts:
  - Choose input method: Enter `1` for coordinates or `2` for addresses.
  - Enable/disable Learner Mode: Enter `y` for safer routes with tips or n for the fastest route.
  - Input start and end points:
    - For coordinates: Provide latitude and longitude (e.g., 38.0382, -84.4992).
    - For addresses: Provide full addresses (e.g., 1234 Rose St, Lexington, KY).

The system will display a route summary, step-by-step directions, and safety information (if in Learner Mode).

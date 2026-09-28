# Marimo Workspace

Interactive data apps, tutorials, and agentic workflows built with [marimo](https://marimo.io).

## Quickstart

### 1. Install Dependencies
Using `uv`:
```bash
uv sync --all-extras
```

Or using standard `pip`:
```bash
pip install -e ".[ai,docs,dev]"
```

### 2. Launch marimo

To create or edit notebooks:
```bash
uv run marimo edit app.py
```

To run as an interactive web application:
```bash
uv run marimo run app.py
```

### 3. Production ASGI Server (Uvicorn)
```bash
uv run uvicorn server:server --host 0.0.0.0 --port 8000
```

## Notebooks & Samples

- **`app.py`**: Interactive dashboard demo with reactive parameters and Altair chart visualization.
- **`hello_world.py`**: Clipboard image paste and reactive widget demonstration.
- **`server.py`**: ASGI wrapper for embedding notebooks into production ASGI / FastAPI servers.

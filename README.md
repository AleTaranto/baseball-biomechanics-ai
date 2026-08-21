# Baseball Biomechanics AI

Baseball Biomechanics AI is an early-stage platform for analyzing baseball swings using video, pose estimation, and biomechanical interpretation. The project is intentionally scoped for incremental delivery: we are starting with a solid repository foundation, a minimal API, and the infrastructure needed to support future vision and biomechanics work.

## Project status

This project is still in its initial bootstrap phase. It is designed to be a modular foundation for future work on:

- video upload and validation;
- frame extraction;
- pose estimation;
- movement reconstruction;
- swing segmentation;
- biomechanical metrics and interpretation;
- actionable coaching feedback.

## Problem and objective

The long-term goal is to help athletes and coaches understand how movement quality, timing, sequencing, and efficiency relate to power generation and injury risk. The system is not intended to replace professional medical advice or coaching judgment. Instead, it aims to provide structured evidence and explanations grounded in biomechanical principles.

## Architecture overview

The repository is organized around a modular architecture:

- `backend/` contains the FastAPI application, configuration, and tests.
- `docs/` stores product, biomechanics, research, and architecture documentation.
- `knowledge/` holds domain knowledge and future rule definitions.
- `specs/` and `tasks/` document API and delivery planning.
- `sample-data/` provides starting metadata for test videos.
- `frontend/` is reserved for future web application work.

## Getting started

### Prerequisites

- Python 3.12+
- pip
- Docker and Docker Compose (for containerized local runs)

### Local environment

```bash
python -m venv .venv
. .venv/bin/activate  # PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- `http://localhost:8000/health`

### Docker

```bash
docker compose up --build
```

The API will be available on:

- `http://localhost:8000/health`

## Running tests

```bash
pytest
```

## Linting and type checking

```bash
ruff check .
mypy backend
```

## Contributing

The project follows an incremental development model. Every future feature should be implemented as a clearly scoped task, with tests, documentation, and verification included in the same change.

See `CONTRIBUTING.md` and `ENGINEERING_PRINCIPLES.md` for contribution standards.

## Roadmap

The current plan is captured in `IMPLEMENTATION_PLAN.md` and `ROADMAP.md`. The repository is intentionally structured to support the next phases without overbuilding the current scope.

## Documentation map

- `ARCHITECTURE.md` ? system overview and module boundaries.
- `IMPLEMENTATION_PLAN.md` ? milestone-based delivery plan.
- `ROADMAP.md` ? prioritized delivery outlook.
- `DECISIONS.md` ? architecture decisions log.
- `ENGINEERING_PRINCIPLES.md` ? rules for future coding agents.
- `docs/` ? product, research, and architecture notes.
- `knowledge/` ? domain knowledge and evidence-driven rules.
- `tasks/` ? task inventory and execution plan.

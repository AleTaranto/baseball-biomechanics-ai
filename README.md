# Baseball Biomechanics AI

[![Status](https://img.shields.io/badge/status-early%20bootstrap-orange)](https://github.com/AleTaranto/baseball-biomechanics-ai)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688)](https://fastapi.tiangolo.com/)

Baseball Biomechanics AI is an early-stage platform for analyzing baseball swings from video, reconstructing movement patterns, and turning raw motion data into explainable biomechanical insights.

The project is intentionally designed for incremental delivery: we start with a stable repository foundation, a minimal API, tested infrastructure, and an architecture that can evolve toward computer vision, pose estimation, and biomechanics analysis without overbuilding the initial phase.

## Why this project exists

The long-term goal is to help athletes, coaches, and analysts understand how movement quality, timing, sequencing, and force transfer relate to performance and potential injury risk.

This is not a medical diagnosis system. Instead, the platform aims to provide structured observations, evidence-based interpretations, and training-oriented feedback grounded in biomechanical principles.

## Current status

This repository is currently in the bootstrap milestone.

The immediate focus is to establish:

- a clean repository structure;
- a working Python/FastAPI backend;
- validation via tests, linting, and type checking;
- containerized local execution;
- CI automation;
- solid documentation and planning artifacts.

## High-level architecture

The repository is organized around a modular architecture:

- `backend/` — API, config, and application bootstrap
- `docs/` — product, research, and architecture documentation
- `knowledge/` — biomechanical knowledge, evidence, and assumptions
- `specs/` — API and product specifications
- `tasks/` — milestone and execution tracking
- `sample-data/` — metadata for test videos and future fixtures
- `frontend/` — reserved for future web UI work

## Key goals

- improve understanding of power transfer and movement efficiency;
- identify mechanical inefficiencies in the kinematic chain;
- detect possible risk-related movement patterns;
- provide actionable, explainable feedback based on biomechanical principles rather than simple comparison against elite athletes.

## Quick start

### Prerequisites

- Python 3.12+
- pip
- Docker and Docker Compose for containerized workflows

### Local development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then visit:

- `http://localhost:8000/health`

### Docker

```bash
docker compose up --build
```

### Test, lint, and type checking

```bash
pytest
ruff check .
mypy backend
```

## Repository map

- `README.md` — project overview and onboarding
- `ARCHITECTURE.md` — system design and boundaries
- `IMPLEMENTATION_PLAN.md` — milestone-based delivery plan
- `ROADMAP.md` — delivery roadmap
- `DECISIONS.md` — architecture decision log
- `ENGINEERING_PRINCIPLES.md` — rules for future coding agents
- `CONTRIBUTING.md` — contribution guidelines
- `docs/` — product and domain documentation
- `knowledge/` — knowledge base for evidence and rules
- `tasks/` — task structure and backlog

## Project board

This repository includes a GitHub Project for tracking milestones and backlog items.

- GitHub Project: https://github.com/users/AleTaranto/projects/1

## Roadmap

The long-term roadmap is organized in milestones covering:

1. repository bootstrap and foundation
2. video ingestion and validation
3. frame extraction and processing
4. pose estimation
5. swing segmentation
6. biomechanical data model
7. metrics engine
8. interpretation and recommendations

See `IMPLEMENTATION_PLAN.md` and `ROADMAP.md` for the full plan.

## Contributing

The project follows an incremental delivery model. Each feature should be implemented as a clearly scoped task with tests, docs, and validation included in the same change.

See:

- `CONTRIBUTING.md`
- `ENGINEERING_PRINCIPLES.md`
- `tasks/README.md`

## Documentation

- `ARCHITECTURE.md`
- `DECISIONS.md`
- `docs/product/vision.md`
- `docs/biomechanics/overview.md`
- `knowledge/README.md`

## Important note

This repository is intentionally in an early stage. The goal is not to ship a complete biomechanical analysis platform in one step, but to create a robust foundation that can evolve safely and predictably.

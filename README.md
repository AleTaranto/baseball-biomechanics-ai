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

This repository is currently in the movement-data foundation milestone.

The project now includes:

- validated video ingestion and metadata persistence;
- frame extraction from uploaded videos with ordered timestamps and frame indices;
- provider-agnostic pose estimation with a MediaPipe implementation;
- a canonical `MovementRecording` model used for downstream motion sequences;
- validation for missing frames, invalid coordinates, and low-confidence joints;
- tests, linting, and type checking for the core pipeline;
- documentation and architecture decisions covering the current boundaries.

At this level, the system is a working local research pipeline for ingesting swing videos and converting them into structured temporal motion data. It is not yet a full biomechanics metrics engine or coaching recommendation system.

## What the project does right now

The current implementation supports a clean sequence:

```text
video upload
  -> validation and metadata persistence
  -> frame extraction
  -> pose estimation
  -> canonical MovementRecording
  -> quality validation
```

The pipeline is intentionally modular:

- `sample-data/uploads/` stores raw uploaded videos and metadata;
- `sample-data/frames/<video_id>/` stores extracted frames and manifests;
- `sample-data/pose-estimation/<video_id>/` stores raw provider output;
- `sample-data/movement/` stores canonical movement JSON records;
- downstream analysis can depend only on `MovementRecording`, not on MediaPipe-specific payloads.

## Quick tutorial: how to use the code so far

### 1) Create the environment

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 2) Start the backend

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- `http://localhost:8000/health`

### 3) Put your sample video in the upload folder

The project expects videos in the repo-local sample-data area for local testing.

```bash
mkdir -p sample-data/uploads
cp /path/to/your-video.mp4 sample-data/uploads/
```

### 4) Upload the video through the API

Use multipart upload to the video route. Example with `curl`:

```bash
curl -X POST "http://localhost:8000/videos/upload" \
  -F "file=@sample-data/uploads/your-video.mp4"
```

The response returns the persisted video metadata, including the generated `video_id`.

### 5) Extract frames

```bash
curl "http://localhost:8000/videos/{video_id}/extract-frames"
```

This writes ordered frames and a manifest to `sample-data/frames/{video_id}/`.

### 6) Run pose estimation

```bash
curl "http://localhost:8000/videos/{video_id}/estimate-pose"
```

The raw provider output is saved under `sample-data/pose-estimation/{video_id}/`.

### 7) Build the canonical movement record

The movement layer converts provider output into the canonical movement model. This happens in code via the movement service and produces a `MovementRecording` JSON under:

```text
sample-data/movement/{video_id}.json
```

### 8) Inspect the output

Most outputs are plain JSON and can be read directly, for example:

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('sample-data/movement/swing1.json')
obj = json.loads(p.read_text())
print(obj['recording_id'])
print(obj['source_video_id'])
print(obj['duration'])
print(len(obj['frames']))
print(obj['quality_summary'])
PY
```

### 9) Run validation locally

```bash
pytest
ruff check .
mypy backend
```

## Repository structure

- `backend/app/services/` — ingestion, frame extraction, pose estimation, and movement mapping logic
- `backend/app/schemas/` — domain data contracts for videos, frames, pose results, and movement
- `backend/tests/unit/` — tests for ingestion, extraction, pose estimation, and movement validation
- `sample-data/uploads/` — raw uploaded video files
- `sample-data/frames/` — extracted frames and manifests
- `sample-data/pose-estimation/` — raw pose provider output
- `sample-data/movement/` — canonical movement records
- `tasks/` — milestone specifications and execution notes

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

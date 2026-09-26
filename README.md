# Baseball Biomechanics AI

[![Status](https://img.shields.io/badge/status-production--ready%20pipeline-green)](https://github.com/AleTaranto/baseball-biomechanics-ai)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688)](https://fastapi.tiangolo.com/)

Baseball Biomechanics AI is an end-to-end computer vision and biomechanical analysis engine for baseball hitting and pitching. It ingests video, extracts high-frequency poses, tracks bat and body kinematics, computes rotational force transfer and timing metrics, and presents interactive visual dashboards for coaches, athletes, and biomechanists.

## Why this project exists

The goal is to help athletes, coaches, and analysts understand how movement quality, timing, kinematic sequencing, force transfer, and body mechanics relate to performance and injury risk reduction.

The platform provides structured observations, evidence-based interpretations, kinematic metrics, and training-oriented feedback grounded in sports biomechanics principles.

## Current status

All 19 execution tasks (Tasks 001–019) across the entire implementation roadmap are complete.

The project includes:

- **Video Ingestion & Validation**: Multi-format video ingestion with framerate and resolution validation.
- **High-Throughput Frame Extraction**: OpenCV decoding with frame caching and manifest tracking.
- **Provider-Agnostic Pose Estimation**: MediaPipe BlazePose keypoint extraction with temporal filtering.
- **Canonical Movement & Kinematic Models**: Unified time-series schemas for joint angles, segment vectors, angular velocities, and accelerations.
- **Swing & Delivery Segmentation**: Automated temporal phase detection (Stance, Load, Stride, Acceleration, Contact, Follow Through; Windup, Cocking, Acceleration, Release, Deceleration).
- **Batting Biomechanical Metrics Engine**: Peak barrel speed, X-Factor hip-shoulder separation, torso tilt, head drift, and hand path calculations.
- **Pitching Biomechanical Analyzer**: Stride length (% body height), arm slot angle, elbow flexion, pelvis/torso angular velocity, and release point metrics.
- **Computer Vision Bat Tracker & Multi-Signal Contact Detector**: Canny/Hough line detection and consensus-based contact frame identification.
- **Two-Pass Performance Pipeline**: Fast downsampled coarse scanning with deep pose processing pruned to active motion windows (achieving >30% compute reduction).
- **Benchmark & Accuracy Suite**: Throughput profilers, FPS speedup multipliers, and precision validation against ground-truth signals.
- **Advanced Visual Overlays & Video Rendering**: Skeleton wireframes, anatomical scaling, 2D bat overlay stabilization with motion trails, pitching stride baselines, arm slot rays, and HUD phase badges burned into MP4 videos.
- **Production REST API**: Full FastAPI route suite (`/api/v1/videos`, `/api/v1/analysis`, `/api/v1/pipeline`, `/api/v1/benchmark`).
- **Interactive Web Visualizer Dashboard**: Modern HTML5/Tailwind/Chart.js web interface served at `/dashboard` with video scrubbing, synced kinematics graphs, overlay toggles, and real-time metric cards.

## What the project does right now

The complete pipeline executes seamlessly:

```text
video upload
  -> validation and metadata persistence
  -> two-pass coarse scan & active window pruning
  -> frame extraction & pose estimation
  -> temporal filtering & canonical MovementRecording
  -> kinematic calculations (angles, velocities)
  -> swing / delivery phase segmentation
  -> batting / pitching biomechanics & bat tracking
  -> multi-signal contact event detection
  -> video visual overlay generation (MP4)
  -> interactive web visualizer dashboard
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

# Baseball Biomechanics AI

[![CI Status](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/AleTaranto/baseball-biomechanics-ai/actions)
[![Status](https://img.shields.io/badge/status-production--ready%20pipeline-green)](https://github.com/AleTaranto/baseball-biomechanics-ai)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688)](https://fastapi.tiangolo.com/)

Baseball Biomechanics AI is an end-to-end computer vision and biomechanical analysis engine for baseball hitting and pitching. It ingests video, extracts high-frequency poses, tracks bat and body kinematics, computes rotational force transfer and timing metrics, and presents interactive visual dashboards for coaches, athletes, and biomechanists.

---

## Why this project exists

The goal is to help athletes, coaches, and analysts understand how movement quality, timing, kinematic sequencing, force transfer, and body mechanics relate to performance and injury risk reduction.

The platform provides structured observations, evidence-based interpretations, kinematic metrics, and training-oriented feedback grounded in sports biomechanics principles.

---

## Current Status & Level of Implementation Achieved

All **12 Milestones** and **19 Execution Tasks** (Tasks 001–019) are **100% complete, fully implemented, and validated** with automated test suites, type safety checks (`mypy`), and linter compliance (`ruff`).

### Implemented Core Capabilities

1. **Video Ingestion & Validation** (`Task 001–003`):
   - Multi-format ingestion (MP4, MOV, AVI) with resolution and frame rate quality gates (e.g. 120 FPS validation).
2. **Frame Extraction & Manifest Service** (`Task 004`):
   - High-throughput OpenCV frame decoding, frame caching, and JSON manifest generation.
3. **Provider-Agnostic Pose Estimation** (`Task 005`):
   - MediaPipe BlazePose landmark extraction with keypoint confidence filtering and debug overlays.
4. **Canonical Movement Model & Filtering** (`Task 007`):
   - Unified `MovementRecording` schema with 4th-order zero-phase Butterworth low-pass temporal filtering and pose sequence quality scoring.
5. **3D & 2D Kinematics Engine** (`Task 008, 012`):
   - Joint angles (elbows, knees, hips, shoulders), segment vectors, linear/angular velocities, accelerations, and generic kinematic primitives.
6. **Swing & Pitching Segmentation** (`Task 006, 016`):
   - Automated detection of batting phases (*Stance, Load, Stride, Acceleration, Contact, Follow Through*) and pitching delivery phases (*Windup, Cocking, Acceleration, Release, Deceleration*).
7. **Batting Biomechanical Metrics Engine** (`Task 009`):
   - X-Factor hip-shoulder separation, torso tilt, head drift, hand path, and proximal-to-distal kinetic chain sequencing.
8. **Pitching Biomechanical Analyzer** (`Task 016`):
   - Stride length (% body height), arm slot angle, elbow flexion, pelvis/torso angular rotational velocities, and release point metrics.
9. **Computer Vision Bat Tracker & Multi-Signal Contact Detector** (`Task 010, 011`):
   - High-precision Chromatic / HSV Marker Bat Tracking (`ColorMarkerBatTracker`), Hough shaft line detection (`ShaftEdgeBatTracker`), hybrid fallback (`HybridBatTracker`), barrel attack angle calculation, and consensus-based contact frame identification.
10. **Two-Pass Performance Pipeline** (`Task 014`):
    - Coarse downsampled scanning with active window pruning, achieving >30% compute reduction.
11. **Benchmark & Accuracy Suite** (`Task 015`):
    - Throughput profilers, FPS speedup multipliers, and kinematic error benchmarking against ground truth.
12. **Advanced Visual Overlays & Video Rendering** (`Task 013, 017`):
    - Anatomically-scaled 3D skeleton models, stabilized 2D bat trajectory trails, arm slot rays, and HUD phase badges burned into MP4 videos.
13. **Production REST API & Interactive Web Visualizer** (`Task 018, 019`):
    - Full FastAPI route suite (`/api/v1/videos`, `/api/v1/analysis`, `/api/v1/pipeline`, `/api/v1/benchmark`) and interactive HTML5/Tailwind/Chart.js Web Dashboard served at `/dashboard`.

---

## End-to-End Pipeline Execution Flow

```text
Video Upload / Input
  │
  ├──► Video Validation & Metadata Persistence
  │
  ├──► Two-Pass Coarse Scanning & Active Window Pruning
  │
  ├──► OpenCV Frame Extraction & Manifest Generation
  │
  ├──► MediaPipe Pose Estimation & Temporal Butterworth Filtering
  │
  ├──► Canonical MovementRecording Generation
  │
  ├──► 2D/3D Kinematic Calculations (Angles, Velocities, Accelerations)
  │
  ├──► Swing / Delivery Phase Temporal Segmentation
  │
  ├──► Batting / Pitching Biomechanics Analysis
  │
  ├──► Chromatic Marker / Edge Bat Tracking & Multi-Signal Contact Detection
  │
  ├──► Video Visual Overlay Generation (Skeleton, Bat Trail, Arm Slot, HUD)
  │
  └──► Web Dashboard (/dashboard) & FastAPI REST Endpoints
```

---

## Quick Start & Usage Guide

### 1) Prerequisites
- Python 3.12+
- Docker & Docker Compose (optional, for containerized run)

### 2) Local Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"
```

### 3) Run Automated Quality Checks & Tests

```bash
# Run pytest unit test suite (100+ tests)
python3 -m pytest

# Run Ruff linter
python3 -m ruff check .

# Run Mypy static type checker
python3 -m mypy backend
```

### 4) Launch the FastAPI Server & Web Dashboard

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once running:
- **Interactive Web Visualizer Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## Repository Map

- `backend/app/api/` — FastAPI REST API endpoints (`videos`, `analysis`, `pipeline`, `benchmark`)
- `backend/app/services/` — Ingestion, Pose Estimation, Kinematics, Segmentation, Bat Tracking, Pitching, Visualizations, and Two-Pass Pipeline
- `backend/app/schemas/` — Pydantic domain models and contracts
- `backend/tests/unit/` — Pytest unit test suite covering all modules
- `frontend/` — Interactive HTML5/Tailwind/Chart.js Web Dashboard served at `/dashboard`
- `docs/` — Architecture, domain model, and biomechanical principles documentation
- `knowledge/` — Biomechanical knowledge base, metrics definitions, and rules
- `tasks/` — Detailed task specifications and execution logs (Tasks 001–019)
- `IMPLEMENTATION_PLAN.md` — Milestone delivery plan and completion status
- `ROADMAP.md` — Long-term product roadmap

---

## Contributing & Development Principles

This repository enforces strict code quality and design standards:
- **Test-Driven Reliability**: Every feature is backed by unit tests (`pytest`).
- **Type Safety**: Full strict type annotations validated by `mypy`.
- **Clean Architecture**: Domain contracts separated from infrastructure and provider logic.

See `CONTRIBUTING.md` and `ENGINEERING_PRINCIPLES.md` for guidelines.

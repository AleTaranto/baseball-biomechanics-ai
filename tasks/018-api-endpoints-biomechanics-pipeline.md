# Task 018 — REST API Endpoints for Full Biomechanics Pipeline

## Objective

Expose the complete suite of computer vision, biomechanical analysis, bat tracking, contact detection, pitching analysis, two-pass execution, and benchmark comparison via production-grade FastAPI REST endpoints.

## Context

According to Section 18 & Section 19 of `plan_extended.txt`:
"18. Architecture requirements:
Expose services through modular APIs separating core computer vision from sport-specific analysis layers (batting and pitching)."

## Scope

- Define canonical pipeline schemas in `backend/app/schemas/pipeline.py`:
  - `PipelineRunRequest`: processing mode (`full`, `half_rate`, `two_pass`), filtering mode, overlay toggle, manual contact override, and handedness override.
  - `PipelineRunResponse`: video metadata, throughput FPS, artifact paths, contact keyframes, bat speed, X-factor separation, stride length, and arm slot metrics.
- Implement analysis routes in `backend/app/api/routes/analysis.py`:
  - `POST /api/v1/analysis/batting/{video_id}` -> `BattingMetricsResult`
  - `POST /api/v1/analysis/pitching/{video_id}` -> `PitchingAnalysisResult`
  - `POST /api/v1/analysis/bat-tracking/{video_id}` -> `BatTrackingResult`
  - `POST /api/v1/analysis/contact/{video_id}` -> `ContactDetectionResult`
- Implement pipeline execution routes in `backend/app/api/routes/pipeline.py`:
  - `POST /api/v1/pipeline/run/{video_id}` -> `PipelineRunResponse`
  - `POST /api/v1/pipeline/two-pass/{video_id}` -> `TwoPassResult`
- Implement benchmarking routes in `backend/app/api/routes/benchmark.py`:
  - `POST /api/v1/benchmark/run/{video_id}` -> `BenchmarkComparisonReport`
- Register routes in `backend/app/main.py`.
- Comprehensive API unit test suite in `backend/tests/unit/test_api_endpoints.py`.

## Acceptance Criteria

- [x] Schemas defined in `backend/app/schemas/pipeline.py`.
- [x] Endpoints for batting, pitching, bat tracking, contact, pipeline execution, two-pass, and benchmarks implemented.
- [x] Routes mounted in FastAPI application.
- [x] 85/85 tests passing with 0 ruff linter errors.

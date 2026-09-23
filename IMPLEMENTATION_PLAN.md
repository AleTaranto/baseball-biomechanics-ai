# Implementation plan

All milestones have been fully implemented and verified with automated test coverage, type safety checks, and linter compliance.

## Milestone 0 — Repository Bootstrap [Completed]
- Repository structure, pyproject.toml, FastAPI core, Docker support, pytest test suite, ruff linting, mypy type checking, GitHub Actions CI pipeline.

## Milestone 1 — Video Ingestion & Validation [Completed]
- Upload endpoints, multi-format validation (MP4, MOV, AVI), FPS/resolution quality gates, and metadata persistence.

## Milestone 2 — Frame Extraction & Processing [Completed]
- OpenCV frame decoding, timestamp synchronization, frame caching, and manifest generation.

## Milestone 3 — Pose Estimation [Completed]
- Provider-agnostic pose interface, MediaPipe BlazePose integration, keypoint tracking, debug overlays, and gap tracking.

## Milestone 4 — Movement Data Model & Validation [Completed]
- Canonical `MovementRecording` model, temporal Butterworth filtering, coordinate normalization, quality scoring, and issue reporting.

## Milestone 5 — Kinematics Engine [Completed]
- Joint angles (elbows, knees, hips, shoulders), segment vectors, linear/angular velocities, and accelerations.

## Milestone 6 — Swing & Pitching Segmentation [Completed]
- Automated detection of batting phases (Stance, Load, Stride, Acceleration, Contact, Follow Through) and pitching delivery windows.

## Milestone 7 — Batting Biomechanical Metrics Engine [Completed]
- X-Factor hip-shoulder separation, torso tilt, head drift, hand path, and kinetic chain proximal-to-distal sequencing analysis.

## Milestone 8 — Computer Vision Bat Tracker & Contact Detector [Completed]
- Canny/Hough shaft edge detection, HSV color marker chromatic segmentation, hybrid bat tracking with fallback, sweet spot tracking, attack angle calculation, and multi-signal consensus contact detection.

## Milestone 9 — Pitching Biomechanical Analyzer [Completed]
- Pitch delivery phase segmentation, stride length (% body height), arm slot angle, elbow flexion, pelvis/torso rotational velocities.

## Milestone 10 — Two-Pass Performance Pipeline & Benchmarking [Completed]
- Downsampled coarse motion scanning, active window pruning (>30% compute reduction), throughput profiler, and accuracy benchmarking suite.

## Milestone 11 — Advanced Visual Overlays & Video Rendering [Completed]
- Anatomically-scaled 3D skeleton wireframe overlays, stabilized 2D bat overlays, bat trajectory trails, arm slot rays, and HUD phase badges burned into video files.

## Milestone 12 — Production REST API & Interactive Web Dashboard [Completed]
- FastAPI endpoints for batting, pitching, pipelines, and benchmarks; interactive HTML5/Tailwind/Chart.js web visualizer dashboard mounted at `/dashboard`.

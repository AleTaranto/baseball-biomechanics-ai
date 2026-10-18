# Roadmap

All phases across the delivery roadmap are 100% complete and fully implemented.

## Phase 1: Bootstrap & Platform Foundation [Completed]

- [x] initialize repository structure;
- [x] enable Python tooling and CI pipeline;
- [x] create FastAPI backend with health and configuration endpoints;
- [x] document project architecture, principles, and guardrails.

## Phase 2: Media Pipeline [Completed]

- [x] ingest and validate video content (FPS and resolution quality gates);
- [x] extract metadata and high-throughput frames with OpenCV;
- [x] prepare task boundaries, caching, and storage manifests.

## Phase 3: Estimation & Motion Reconstruction [Completed]

- [x] integrate MediaPipe BlazePose estimation;
- [x] store canonical movement data (`MovementRecording`);
- [x] apply zero-phase Butterworth temporal low-pass filtering;
- [x] define object, joint, and biomechanical event schemas.

## Phase 4: Biomechanics & Interpretation [Completed]

- [x] calculate 2D/3D kinematic metrics (angles, velocities, accelerations);
- [x] calculate batting metrics (X-factor, torso tilt, hand path, proximal-to-distal sequencing);
- [x] calculate pitching metrics (stride length, arm slot angle, rotational velocities);
- [x] track bat via chromatic marker and shaft edge algorithms;
- [x] multi-signal consensus contact detection;
- [x] two-pass coarse-to-fine performance pipeline with active window pruning.

## Phase 5: Product Experience & Visualizer [Completed]

- [x] 3D anatomically scaled wireframe and 2D bat/arm-slot overlay rendering;
- [x] HUD phase badges, contact banners, and video export;
- [x] production REST API routes (`/api/v1/videos`, `/api/v1/analysis`, `/api/v1/pipeline`, `/api/v1/benchmark`);
- [x] interactive HTML5/Tailwind/Chart.js Web Visualizer Dashboard mounted at `/dashboard`.

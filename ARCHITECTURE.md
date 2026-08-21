# Architecture

## Overview

Baseball Biomechanics AI is designed as an incremental platform that separates domain concerns while keeping early phases lightweight and easy to test. The core architectural principle is to keep the pipeline modular: source media, processing, domain model, metrics, interpretation, and user-facing outputs remain independent where possible.

## Main modules

### Backend API

The FastAPI application provides the service boundary for health checks and future endpoints. It should stay thin and delegate to domain services rather than containing detailed business logic.

### Domain layer

The domain layer defines the conceptual entities of the system: athlete, video, processed frames, keypoints, events, and metrics. This layer should not depend on infrastructure concerns such as storage or HTTP.

### Services

Services orchestrate workflows, such as video validation, frame extraction, or swing segmentation. They use domain objects and are intentionally separated from the API layer.

### Infrastructure

Infrastructure concerns include configuration, persistence abstractions, object storage hooks, and integration adapters. These are isolated behind service interfaces and repository boundaries.

### Computer vision and biomechanics

The computer vision and biomechanics pipeline is deliberately kept separate. The vision subsystem produces measurable data from media; the biomechanics engine interprets those measurements using domain rules and evidence-based constraints.

## Data flow

```text
Video input
  -> validation
  -> frame extraction
  -> pose estimation
  -> movement reconstruction
  -> swing segmentation
  -> biomechanical metrics
  -> interpretation
  -> recommendation/reporting
```

## Architectural boundaries

- Media ingestion and validation should not own interpretation logic.
- Pose estimation should not directly expose business rules.
- Keypoint outputs should remain structured and provider-agnostic so the model can change without rewriting the pipeline.
- Biomechanics metrics must remain inspectable and traceable to evidence.
- API handlers should validate inputs and coordinate operations, not implement complex algorithms.

## Pose estimation layer

The pose estimation subsystem follows an explicit abstraction boundary. An abstract `PoseEstimator` interface defines the contract for producing per-frame keypoints, while the concrete provider implementation is isolated behind that interface. This allows the project to start with MediaPipe and later replace it with a different model or package without changing the rest of the pipeline.

Each frame result includes:

- frame index;
- timestamp in milliseconds;
- detection status for the frame;
- required human keypoints (shoulders, elbows, wrists, hips, knees, ankles);
- normalized coordinates and visibility/confidence when available;
- explicit tracking for frames where no person was detected.

## Movement data model layer

The movement layer sits downstream of raw pose outputs and creates a provider-independent temporal representation. It converts raw per-frame keypoints into a standard `MovementRecording` object, preserves ordering by frame index and timestamp, and keeps the data in a format understandable by future biomechanics features.

This layer is responsible for:

- normalizing provider-specific keypoint payloads into canonical joint names;
- preserving the temporal sequence and frame metadata;
- validating missing frames, missing joints, invalid coordinates, low confidence, and temporal discontinuities;
- emitting a structured quality summary without attempting automatic correction.

The model explicitly avoids smoothing, interpolation, or metric-specific inference at this stage.

### Canonical movement contract

`MovementRecording` is the canonical source of truth for movement data used by downstream modules. It is the contract that future kinematic analysis, swing segmentation, and biomechanics logic should consume.

Important constraints:

- `timestamp` values are expressed in milliseconds since the start of the recording;
- `duration` is expressed in milliseconds as the total elapsed time of the recording;
- all provider-specific time units are normalized at the adapter boundary;
- downstream consumers must depend only on `MovementRecording` and not on raw pose-provider payloads.

Raw pose-estimation provider outputs remain technical artifacts for:

- debugging;
- provenance;
- model/provider audit;
- reproducibility.

They are not the domain-level contract for downstream processing. A provider-specific payload should be converted through an adapter and then discarded by the domain pipeline unless it is needed for traceability.

## Evolution

The first milestone focuses on repository bootstrap and API health. The next milestones add video ingestion, frame extraction, pose estimation, and eventually a metrics and interpretation engine. The architecture is intentionally designed to support this growth without overbuilding the initial implementation.

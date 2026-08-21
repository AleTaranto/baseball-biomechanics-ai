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
- Biomechanics metrics must remain inspectable and traceable to evidence.
- API handlers should validate inputs and coordinate operations, not implement complex algorithms.

## Evolution

The first milestone focuses on repository bootstrap and API health. The next milestones add video ingestion, pose estimation, and eventually a metrics and interpretation engine. The architecture is intentionally designed to support this growth without overbuilding the initial implementation.

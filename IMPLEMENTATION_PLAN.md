# Implementation plan

## Milestone 0 ? Repository Bootstrap

- repository structure;
- minimal backend;
- Docker support;
- test suite;
- linting and type checking;
- CI pipeline.

## Milestone 1 ? Video Ingestion

- upload support;
- format validation;
- metadata extraction;
- robust error management.

## Milestone 2 ? Video Processing

- frame extraction;
- FPS and resolution handling;
- processing pipeline orchestration.

## Milestone 3 ? Pose Estimation

- define a provider-agnostic pose-estimation interface;
- integrate an initial model/provider (MediaPipe-based);
- produce structured keypoint outputs for required joints;
- persist results in a JSON manifest for each processed video;
- track detection gaps, confidence, and missing poses without auto-correction.

## Milestone 4 ? Movement Data Model and Validation

- define a provider-independent movement recording model;
- map raw pose output to a standardized temporal representation;
- validate frame ordering, timestamps, missing joints, low confidence, invalid coordinates, and temporal gaps;
- emit a quality summary without applying smoothing or interpolation.

## Milestone 5 ? Swing Segmentation

- detection of major swing phases;
- structured temporal outputs.

## Milestone 6 ? Biomechanical Data Model

- joints, body segments, angles, velocities, accelerations, and events.

## Milestone 7 ? Biomechanical Metrics Engine

- geometric, temporal, and kinetic-chain metrics.

## Milestone 7 ? Biomechanical Interpretation

- rules, evidence, confidence, explanations, and separation between observations and inferences.

## Incremental delivery strategy

This project will proceed one milestone at a time. Each milestone must leave the main branch in a stable, testable state. No milestone should be started before the previous one has been validated and documented.

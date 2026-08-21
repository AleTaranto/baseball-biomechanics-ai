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

- integration with an initial model/provider;
- structured keypoint outputs;
- result persistence;
- confidence tracking.

## Milestone 4 ? Swing Segmentation

- detection of major swing phases;
- structured temporal outputs.

## Milestone 5 ? Biomechanical Data Model

- joints, body segments, angles, velocities, accelerations, and events.

## Milestone 6 ? Biomechanical Metrics Engine

- geometric, temporal, and kinetic-chain metrics.

## Milestone 7 ? Biomechanical Interpretation

- rules, evidence, confidence, explanations, and separation between observations and inferences.

## Incremental delivery strategy

This project will proceed one milestone at a time. Each milestone must leave the main branch in a stable, testable state. No milestone should be started before the previous one has been validated and documented.

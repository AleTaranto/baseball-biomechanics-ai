# Task 010 — Bat Tracking & Trajectory Analysis

## Objective

Implement a standalone bat tracking pipeline module (`BatTracker`) to detect the bat shaft, track barrel and sweet spot coordinates over time, calculate rotational speed / angular velocity, estimate impact timing, and compute the vertical attack angle at contact.

## Context

According to Section 9 of `plan_extended.txt`, bat tracking must remain modular and capable of operating independently from body pose estimation. Extracting accurate bat kinematics (shaft angle, barrel velocity, sweet spot position, and trajectory attack angle) provides the essential link between batter biomechanics (pelvis/torso sequence) and ball exit velocity.

## Scope

- Define canonical Pydantic schemas in `backend/app/schemas/bat.py`:
  - `BatDetection`: single-frame detection of handle, barrel, sweet spot, shaft orientation, and confidence.
  - `BatTrajectoryPoint`: kinematic metrics (barrel linear speed, shaft orientation angle, angular velocity).
  - `BatTrackingResult`: full recording trajectory, tracking coverage, peak barrel speed, estimated contact frame, and attack angle at contact.
- Implement extensible tracker interface and detector in `backend/app/services/bat_tracker_service.py`:
  - `BaseBatTracker`: abstract interface for bat trackers.
  - `ShaftEdgeBatTracker`: edge gradient analysis (Canny + probabilistic Hough transform) with hand anchor priors and geometric length filtering.
  - Automatic sweet spot computation (~75% along shaft from handle toward barrel).
  - Short gap interpolation (up to 3 consecutive missed frames) to handle motion blur during explosive downswing.
  - Calculation of barrel speed ($\Delta p / \Delta t$) and angular velocity ($\Delta \theta / \Delta t$).
  - Vertical attack angle calculation relative to horizontal swing plane.
- Persist results under `sample-data/bat-tracking/{video_id}.json`.
- Integrate directly into `run_pipeline.py` with performance profiling.

## Out of Scope

- Real-time deep learning bat segmentation model training (YOLOv8-pose custom fine-tuning) — to be added as an alternate provider.
- Ball trajectory and aerodynamic pitch flight tracking.

## Acceptance Criteria

- [x] Abstract tracker and canonical edge/shaft detector implemented in `backend/app/services/bat_tracker_service.py`.
- [x] Schemas defined in `backend/app/schemas/bat.py`.
- [x] Sweet spot and shaft orientation calculated accurately.
- [x] Linear barrel speed and angular velocity computed across frames.
- [x] Attack angle calculation at contact frame verified.
- [x] Short gaps interpolated across motion blur frames.
- [x] Unit test suite passing in `backend/tests/unit/test_bat_tracker.py`.
- [x] End-to-end integration and profiling verified in `run_pipeline.py`.

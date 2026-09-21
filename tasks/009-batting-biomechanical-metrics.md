# Task 009 — Batting Biomechanical Metrics

## Objective

Calculate core baseball batting biomechanical metrics, including pelvis-torso rotational separation (X-Factor), posture tracking (torso inclination, head drift), hand path kinematics, and proximal-to-distal kinematic sequence verification.

## Context

Following motion segmentation (Task 006), the platform requires specialized sport-specific biomechanical metrics to evaluate hitter mechanics. These metrics evaluate power generation efficiency, rotational sequencing, balance, and barrel path mechanics across the swing phases.

## Scope

- Implement `BattingMetricsService` and corresponding Pydantic schemas (`backend/app/schemas/batting.py`):
  - **Rotational Kinematics & X-Factor**:
    - Pelvis rotation angle and angular velocity.
    - Torso/shoulder rotation angle and angular velocity.
    - Shoulder-hip separation angle ($\Delta\theta_{\text{separation}} = |\theta_{\text{shoulder}} - \theta_{\text{hip}}|$).
    - Maximum shoulder-hip separation and frame index at peak.
  - **Posture & Balance Tracking**:
    - Torso forward/lateral inclination angle relative to vertical.
    - Head drift from initial stance position in horizontal and vertical directions.
  - **Hand Path Kinematics**:
    - Total hand path distance traversed during the downswing.
    - Hand-to-body center distance at contact/impact.
    - Peak hand speed and contact hand speed.
  - **Kinematic Sequence Analysis**:
    - Identification of peak angular/linear speeds for pelvis, torso, and lead wrist.
    - Peak timing sequencing verification (`pelvis` $\rightarrow$ `torso` $\rightarrow$ `hands`).
    - Computation of transfer time intervals ($\Delta t$) between segment velocity peaks.
    - Flag `is_proximal_to_distal` assessing kinetic energy transfer efficiency.
- Persist results under `sample-data/batting-metrics/{video_id}.json`.
- Integrate execution and profiling directly into `run_pipeline.py`.

## Out of Scope

- Computer-vision bat segmentation / shaft tracking (covered in Task 011).
- Pitching mechanics analysis (Phase 4).
- 3D inverse dynamics joint torque estimation.

## Acceptance Criteria

- [x] Biomechanical calculation service implemented in `backend/app/services/batting_metrics_service.py`.
- [x] Pydantic schemas defined in `backend/app/schemas/batting.py`.
- [x] X-factor / hip-shoulder separation calculated accurately across swing frames.
- [x] Kinematic sequence peak extraction and proximal-to-distal evaluation implemented.
- [x] Hand path length and distance-to-body at contact computed.
- [x] Unit test suite created with synthetic swing kinematics verifying calculation accuracy.
- [x] Pipeline integration completed in `run_pipeline.py` with performance profiling.

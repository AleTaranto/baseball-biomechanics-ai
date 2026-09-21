# Task 006 — Swing Segmentation

## Objective

Segment baseball video motion recordings into discrete, meaningful kinematic phases and identify critical swing events (onset, peak hand speed, and estimated bat-ball contact).

## Context

Raw pose tracking provides a continuous stream of coordinate data. Downstream biomechanical analysis (such as kinetic sequencing, hip-shoulder separation, and maximum velocities) requires reliable temporal alignment anchored on athletic events (load, downswing, impact, and follow-through).

## Scope

- Implement an action-agnostic motion segmenter abstraction (`BaseMotionSegmenter`).
- Implement a dedicated `BattingSwingSegmenter` consuming canonical `MovementRecording` and optional `KinematicRecording`.
- Identify candidate swing action windows using kinetic energy and wrist velocity profiles.
- Identify temporal phases:
  - `stance`: baseline preparation before action initiation.
  - `load`: negative/repositioning movement of hands away from the pitcher.
  - `downswing`: explosive forward acceleration toward the impact zone.
  - `follow_through`: rotational deceleration following peak speed/impact.
- Identify milestone events:
  - `load_start`
  - `peak_hand_speed`
  - `contact` (estimated impact zone using deceleration onset inflection).

## Out of Scope

- Pitching delivery phases (reserved for P4 `PitchingAnalyzer`).
- Automatic pitch outcome tracking (hit vs miss).
- Manual coach keyframe annotation UI.

## Output Contract

The canonical output is a `SwingSegmentationResult` schema (`backend/app/schemas/segmentation.py`):
- `recording_id`: associated recording identifier.
- `swing_detected`: boolean flag.
- `total_swings_found`: number of candidate swing windows found.
- `candidate_swings`: list of `SwingWindow` objects, each containing:
  - `start_frame`, `end_frame`, `duration_seconds`
  - `peak_speed_frame`, `peak_hand_speed`
  - `contact_frame`, `contact_time_seconds`
  - `phases`: list of `TemporalPhase`
  - `events`: list of `SwingEvent`

## Acceptance Criteria

- [x] Abstract base segmenter and baseball batting segmenter implemented.
- [x] Swings detected reliably from hand velocity curves above minimum threshold.
- [x] Downswing, follow-through, and load phases segmented with temporal timestamps.
- [x] Contact/impact and peak speed events identified.
- [x] Idle non-swing motion properly rejected (`swing_detected=False`).
- [x] Unit tests pass and integration wired into `run_pipeline.py`.

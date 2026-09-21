# Task 011 — Dedicated Contact / Impact Event Detector

## Objective

Implement a dedicated, multi-signal impact detector (`ContactEventDetector`) that consolidates bat trajectory, hand kinematics, and motion segmentation into an authoritative contact frame, with support for coach / manual keyframe confirmation.

## Context

As noted in Section 10 of `plan_extended.txt`:
"Develop a dedicated event detector. Possible signals: bat trajectory, ball trajectory, hand trajectory, sudden motion changes, visual contact. Initially support manual confirmation of contact frame. Later automate it. Accuracy of contact timing is particularly important because many downstream biomechanical measurements depend on it."

## Scope

- Define canonical Pydantic schemas in `backend/app/schemas/contact.py`:
  - `ContactSignalEntry`: individual signal source, estimated frame, confidence, and explanation.
  - `ContactDetectionResult`: authoritative contact frame, timestamp, confidence, `is_manual_override` flag, component signals, and `consensus_spread_frames`.
- Implement `ContactEventDetector` in `backend/app/services/contact_detector_service.py`:
  - **Signal Integration**:
    - Bat barrel maximum velocity and deceleration inflection (Task 010).
    - Swing segmentation impact events (Task 006).
    - Lead/trail wrist deceleration inflection within the active swing window.
  - **Consensus & Confidence Resolution**:
    - Weighted average across agreeing signals.
    - Dynamic confidence calculation factoring in signal spread and individual weights.
    - Graceful fallback for non-swing or ambiguous recordings.
  - **Manual Override Support**:
    - User/coach keyframe parameter `manual_contact_frame` with top priority, setting `is_manual_override=True` and `confidence=1.0`.
- Persist results under `sample-data/contact-events/{video_id}.json`.
- Integrate directly into `run_pipeline.py` with performance profiling and CLI flag `--manual-contact-frame`.

## Acceptance Criteria

- [x] Canonical schemas defined in `backend/app/schemas/contact.py`.
- [x] Multi-signal detector service implemented in `backend/app/services/contact_detector_service.py`.
- [x] Automated consensus between bat barrel peak speed and wrist deceleration.
- [x] Manual override properly flags and sets exact keyframe with 100% confidence.
- [x] Unit test suite created and verified in `backend/tests/unit/test_contact_detector.py`.
- [x] Integration wired into `run_pipeline.py` with persistence and performance profiling.

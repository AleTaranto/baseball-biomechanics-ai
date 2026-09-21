# Task 016 — Pitching Biomechanical Analysis Engine

## Objective

Implement a specialized `PitchingAnalyzer` and domain schemas for pitching biomechanics, delivery phase segmentation, throwing arm mechanics, stride characteristics, and kinetic chain sequencing, consuming the action-agnostic `BiomechanicsEngine`.

## Context

According to Section 18 of `plan_extended.txt`:
"18. Pitching support (separato ma parallelo):
- Modelli di movimento paralleli per il pitching:
  - fasi del lancio: setup, leg lift, stride, arm cocking, acceleration, release, follow through
  - metriche specifiche: lunghezza del passo (stride), angolo del ginocchio al foot strike, flessione del tronco, angolo del braccio al rilascio (arm slot), massima rotazione esterna della spalla (layback), timing della catena cinetica.
  - architettura modulare per condividere l'engine geometrico/cinematico ma separare la logica sport-specifica."

## Scope

- Define canonical schemas in `backend/app/schemas/pitching.py`:
  - `PitchingPhaseType` & `PitchingPhase`: setup, leg_lift, stride, arm_cocking, acceleration, ball_release, follow_through.
  - `PitchingBiomechanicalMetrics`: handedness (RHP / LHP), normalized stride length, lead knee angle at foot strike and release, maximum hip-shoulder separation, trunk forward/lateral tilt at release, arm slot angle relative to horizontal, elbow flexion at foot strike, release height and extension, kinematic sequence ordering (`pelvis -> trunk -> arm -> hand`).
  - `PitchingDeliveryWindow` & `PitchingAnalysisResult`: milestone frames (leg lift, foot strike, ball release), peak hand speed, and phases.
- Implement `PitchingAnalyzer` in `backend/app/services/pitching_analyzer_service.py`:
  - Automated handedness detection (`RHP` vs `LHP`) from wrist velocities with manual override support.
  - Delivery milestone detection based on lead knee elevation and throwing hand acceleration peaks.
  - Metric computation strictly reusing `BiomechanicsEngine` geometric primitives.
- Unit tests in `backend/tests/unit/test_pitching_analyzer.py`.

## Acceptance Criteria

- [x] Schemas defined in `backend/app/schemas/pitching.py`.
- [x] Handedness auto-detection (`RHP`/`LHP`) and manual override.
- [x] Temporal phase segmentation for pitching deliveries.
- [x] Biomechanical calculations for stride, knee flexion, trunk tilt, arm slot, and separation.
- [x] Unit test suite passing with 100% green tests (77/77 total tests).

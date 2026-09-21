# Task 017 — Pitching Biomechanical Visual Overlays

## Objective

Extend `InspectionService` with pitching-specific biomechanical visual overlays, including throwing hand motion trajectory trails, stride baseline indicators at foot strike, arm slot vector projection at ball release, real-time pitching HUD metrics, and delivery release event banners.

## Context

According to Section 13 & Section 19 (P4, item 27) of `plan_extended.txt`:
"13. Visualization:
Future pitching-specific:
- stride
- arm path
- release point
- pitching phase
27. pitching-specific visualization."

## Scope

- In `backend/app/services/inspection_service.py`:
  - Extend `render_action_hud`:
    - Display current delivery phase badge (e.g. `PHASE: STRIDE`, `PHASE: ARM_COCKING`, `PHASE: RELEASE`).
    - Display real-time pitcher handedness and arm slot angle (`Pitcher: RHP`, `Arm Slot: 45.0 deg`).
    - Display ball release flash banner (`>> BALL RELEASE (2.5 px/s) <<`).
  - Implement `render_pitching_overlay`:
    - Throwing hand decaying motion trail with variable opacity and line thickness.
    - Stride length baseline connection between lead ankle and trail ankle at foot strike keyframe.
    - Arm slot indicator ray along humerus at ball release keyframe with angle readout.
  - Wire pitching overlays into `render_frame_overlay`, `render_overlay_video`, and `generate_inspection_bundle`.
- Unit test in `backend/tests/unit/test_visualization.py` (`test_render_pitching_overlay_and_action_hud`).

## Acceptance Criteria

- [x] Pitching HUD badges and release banners rendered in `render_action_hud`.
- [x] Stride baseline and arm slot ray rendered in `render_pitching_overlay`.
- [x] Full integration in `render_frame_overlay`, `render_overlay_video`, and bundle generator.
- [x] All 78 tests passing with 0 linter errors.

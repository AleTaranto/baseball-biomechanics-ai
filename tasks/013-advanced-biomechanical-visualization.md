# Task 013 — Action-Specific Overlays & Advanced Biomechanical Visualization

## Objective

Enhance the video inspection and visual overlay engine (`InspectionService`) to superimpose domain-specific baseball batting biomechanics: bat shaft and barrel tracking, sweet spot reticle, temporal motion trail, real-time swing phase HUD badge, X-Factor angle readout, and contact/impact flash indicator.

## Context

According to Section 13 of `plan_extended.txt`:
"Create a generic visualization system supporting action-specific overlays. Common: skeleton, keypoints, confidence, trajectories, frame number, timestamp, FPS, processing time. Batting-specific: bat trajectory, contact frame, swing phase, hand path, hip/shoulder rotation."

## Scope

- Enhance `InspectionService` (`backend/app/services/inspection_service.py`):
  - **Bat implement visualization**:
    - High-visibility shaft line (vibrant orange `(0, 140, 255)`).
    - Handle knob marker (white circle).
    - Barrel tip marker (red inner circle with white outline).
    - Sweet spot targeting reticle (cyan/yellow dual ring at ~75% along shaft).
    - Recent barrel positions motion trail (6-frame decaying spline/lines).
  - **Action-Specific HUD**:
    - Real-time athletic phase badge in upper-right corner (`PHASE: STANCE`, `PHASE: LOAD`, `PHASE: DOWNSWING`, `PHASE: FOLLOW_THROUGH`).
    - Live X-Factor hip-shoulder rotational separation readout (`X-Factor: XX.X deg`).
    - High-impact contact frame banner (`>> IMPACT / CONTACT <<`) flashing during estimated impact frames ($\pm 1$ frame).
  - **Downstream Pipeline Execution**:
    - Reordered pipeline stages in `run_pipeline.py` so that `inspection_bundle_generation` executes downstream of `segmentation`, `batting_metrics`, `bat_tracking`, and `contact_detection`, rendering all composite layers onto the final video.
- Test coverage in `backend/tests/unit/test_visualization.py`:
  - `test_render_bat_overlay_and_action_hud` verifying graphical drawing of bat markers, trails, and HUD elements.

## Acceptance Criteria

- [x] Bat shaft, barrel, sweet spot, and temporal motion trail rendered cleanly.
- [x] Active swing phase badge displayed in top-right HUD.
- [x] Contact/impact event highlighted with centered flash banner on impact frames.
- [x] Live X-Factor separation displayed under metadata overlay.
- [x] Pipeline generates synchronized 30/60/120 FPS MP4 video inspection bundle with complete biomechanical layers.
- [x] Unit tests pass (15/15 visualization tests).

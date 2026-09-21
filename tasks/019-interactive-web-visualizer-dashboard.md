# Task 019 — Interactive Web Visualizer Dashboard

## Objective

Build and serve an interactive, dependency-free web visualizer dashboard allowing coaches, biomechanists, and analysts to upload baseball videos, inspect frame-by-frame synchronized kinematics, toggle biomechanical overlays, and review batting/pitching metrics in real time.

## Context

According to Section 1 & Section 19 of `plan_extended.txt`:
"Visualization / UI layer:
Visual confirmation layer over raw video frames with interactive scrubbing, phase landmarks, joint angles, kinematics curves, and HUD overlays."

## Scope

- Create responsive modern frontend interface in `frontend/index.html`:
  - Tailwind CSS layout with dark theme.
  - Video player with frame scrubber, frame-step buttons (±1 frame, ±5 frames), and playback rate controls (0.1x to 1.0x).
  - Canvas overlay toggle panel: skeleton wireframe, bat trajectory trail, pitching stride line, arm slot ray, and contact/release flash HUDs.
  - Biomechanical KPI cards for Batting (Max Bat Speed, Max X-Factor, Torso Tilt, Head Drift) and Pitching (Max Pelvis/Torso Angular Velocity, Stride Length % Height, Max Shoulder External Rotation, Arm Slot Angle).
  - Chart.js kinematics canvas for temporal curves (Angular Velocity, Wrist Speed, X-Factor Separation) synchronized to the video scrubber cursor.
  - Video upload & pipeline runner controls for instant evaluation.
- Implement client-side logic in `frontend/app.js`:
  - Scrubber synchronization between HTML5 `<video>` and Chart.js timestamp vertical guide.
  - Dynamic HUD status badges showing current phase (Stance, Load, Stride, Acceleration, Contact, Follow Through, Windup, Arm Cocking, Acceleration, Deceleration).
  - Asynchronous fetch clients for `/api/v1/pipeline/run/{video_id}`, `/api/v1/benchmark/run/{video_id}`, and `/api/v1/videos/upload`.
  - Responsive Chart.js graph instantiation and data updates.
- Mount static files in FastAPI backend (`backend/app/main.py`) at `/dashboard`.
- Expose `dashboard_url` in the root `/` API greeting endpoint.
- Verify health checks and dashboard static serving via unit tests in `backend/tests/unit/test_health.py`.

## Acceptance Criteria

- [x] Responsive HTML5/Tailwind dashboard created in `frontend/index.html`.
- [x] Scrubber synchronization and API integration in `frontend/app.js`.
- [x] Static mounting at `/dashboard` in `backend/app/main.py`.
- [x] Test suite passing with 86/86 tests green and 0 ruff linter errors.

# Task 014 — Two-Pass Pipeline & Frame Reduction Optimization

## Objective

Implement a two-pass video processing architecture (Strategy F from Section 15 of `plan_extended.txt`):
- **Pass 1**: Rapid, coarse-grained motion scan across temporal frames using downsampled image difference energy to isolate candidate action windows.
- **Pass 2**: Deep, high-framerate kinematic analysis, bat tracking, and pose estimation restricted exclusively to identified active windows.

## Context

High-framerate baseball capture (120-240 FPS or long batting practice rounds) contains significant idle periods (hitter setup, ball retrieval, stance adjustments). Running full deep pose inference and kinematic calculations across all frames wastes compute. A two-pass architecture prunes idle margins while preserving 100% temporal fidelity across the swing action.

## Scope

- Define canonical Pydantic schemas in `backend/app/schemas/two_pass.py`:
  - `TwoPassConfig`: scan sampling interval, window safety padding margin.
  - `ActionWindow`: temporal segment bounding the detected athletic movement.
  - `TwoPassResult`: frame accounting (scanned, evaluated, total) and `compute_reduction_percentage`.
- Implement `TwoPassPipelineService` in `backend/app/services/two_pass_pipeline_service.py`:
  - Normalized motion energy difference computation (`compute_frame_difference_energy`).
  - Pass 1 coarse scan (`scan_video_for_action_windows`) with cluster merging and padding.
  - Compute reduction evaluation (`evaluate_savings`).
- Integrate into `run_pipeline.py`:
  - Add `two_pass` to `--processing-mode` choices.
  - Profile coarse scan stage (`two_pass_coarse_scan`).
  - Dynamically prune input frames to `PoseEstimationService`.
  - Include savings statistics in pipeline result.
- Implement unit tests in `backend/tests/unit/test_two_pass_pipeline.py`.

## Acceptance Criteria

- [x] Schemas defined in `backend/app/schemas/two_pass.py`.
- [x] Pass 1 motion energy detector and window segmenter implemented.
- [x] Savings calculator verified across synthetic benchmarks.
- [x] CLI flag `--processing-mode two_pass` supported in `run_pipeline.py`.
- [x] Unit test suite passing (3/3 two-pass tests, 72/72 total tests).

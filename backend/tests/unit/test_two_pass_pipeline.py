from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from app.schemas.two_pass import ActionWindow, TwoPassConfig
from app.services.two_pass_pipeline_service import TwoPassPipelineService


def test_two_pass_motion_energy_calculation() -> None:
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.zeros((100, 100, 3), dtype=np.uint8)

    # Identical images have 0 energy
    e_zero = TwoPassPipelineService.compute_frame_difference_energy(img1, img2)
    assert e_zero == 0.0

    # Draw white square on img2
    cv2.rectangle(img2, (20, 20), (80, 80), (255, 255, 255), -1)
    e_diff = TwoPassPipelineService.compute_frame_difference_energy(img1, img2)
    assert e_diff > 0.1


def test_two_pass_scan_detects_action_window(tmp_path: Path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Generate 20 synthetic frames:
    # 0..6 static black
    # 7..11 moving bright object
    # 12..19 static black
    for i in range(20):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        if 7 <= i <= 11:
            # draw moving square
            cx = 10 + (i - 7) * 12
            cv2.rectangle(frame, (cx, 30), (cx + 15, 50), (255, 255, 255), -1)
        cv2.imwrite(str(frames_dir / f"frame_{i:04d}.png"), frame)

    cfg = TwoPassConfig(scan_sampling_interval=2, window_padding_seconds=0.05)
    windows = TwoPassPipelineService.scan_video_for_action_windows(
        frames_dir=frames_dir,
        fps=30.0,
        config=cfg,
        motion_threshold=0.01,
    )

    assert len(windows) >= 1
    w = windows[0]
    # Window should comfortably bound the motion segment
    assert w.start_frame <= 7
    assert w.end_frame >= 11


def test_two_pass_compute_reduction_savings() -> None:
    # 100 total frames video, with a single action window of 15 frames
    windows = [
        ActionWindow(
            start_frame=40,
            end_frame=54,
            start_time_seconds=1.33,
            end_time_seconds=1.80,
        )
    ]
    cfg = TwoPassConfig(scan_sampling_interval=4, window_padding_seconds=0.3)
    result = TwoPassPipelineService.evaluate_savings(
        video_id="video-test-100",
        total_frames=100,
        action_windows=windows,
        config=cfg,
    )

    assert result.total_video_frames == 100
    assert result.pass1_scanned_frames == 25  # 100 / 4
    assert result.pass2_analyzed_frames == 15  # frames 40..54 inclusive
    assert result.total_processed_frames == 40  # 25 + 15
    assert result.compute_reduction_percentage == 60.0  # 100 - 40 = 60%

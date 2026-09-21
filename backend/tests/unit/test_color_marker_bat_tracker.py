from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from app.main import app
from app.schemas.bat import BatTrackingResult
from app.schemas.movement import FramePose, JointObservation, MovementRecording, PoseSequenceQuality
from app.services.bat_tracker_service import (
    COLOR_PRESETS,
    ColorMarkerBatTracker,
    HybridBatTracker,
)
from fastapi.testclient import TestClient


def _create_synthetic_marker_image(
    handle_pos: tuple[int, int] = (100, 150),
    barrel_pos: tuple[int, int] = (300, 150),
    handle_bgr: tuple[int, int, int] = (0, 120, 255),    # Bright orange in BGR
    barrel_bgr: tuple[int, int, int] = (50, 230, 50),     # Bright green in BGR
    width: int = 400,
    height: int = 300,
) -> np.ndarray:
    """Create a synthetic test image with two distinct colored circular blobs."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Draw dark background resembling baseball field / batting cage
    img[:] = (30, 30, 30)

    # Draw handle marker (circle)
    cv2.circle(img, handle_pos, 12, handle_bgr, -1)
    # Draw barrel marker (circle)
    cv2.circle(img, barrel_pos, 16, barrel_bgr, -1)
    # Draw gray shaft connecting them
    cv2.line(img, handle_pos, barrel_pos, (70, 70, 70), 3)

    return img


def test_color_presets_exist() -> None:
    assert "neon_green_orange" in COLOR_PRESETS
    assert "neon_orange_green" in COLOR_PRESETS
    assert "yellow_pink" in COLOR_PRESETS

    for name, p in COLOR_PRESETS.items():
        assert "barrel" in p
        assert "handle" in p
        assert len(p["barrel"][0]) == 3
        assert len(p["barrel"][1]) == 3


def test_color_marker_tracker_detect_synthetic_image() -> None:
    tracker = ColorMarkerBatTracker(color_preset="neon_green_orange")
    img = _create_synthetic_marker_image(
        handle_pos=(100, 150),
        barrel_pos=(300, 150),
        handle_bgr=(0, 140, 255),  # Orange
        barrel_bgr=(0, 255, 0),    # Pure Green
        width=400,
        height=300,
    )

    result = tracker.detect_in_image(img, hand_anchor=(0.25, 0.50))
    assert result is not None
    handle, barrel, conf = result

    # Check normalized coordinates: handle at x=100/400=0.25, barrel at x=300/400=0.75
    assert math.isclose(handle[0], 0.25, abs_tol=0.04)
    assert math.isclose(handle[1], 0.50, abs_tol=0.04)
    assert math.isclose(barrel[0], 0.75, abs_tol=0.04)
    assert math.isclose(barrel[1], 0.50, abs_tol=0.04)
    assert conf >= 0.80


def test_color_marker_tracker_barrel_with_hand_anchor_fallback() -> None:
    tracker = ColorMarkerBatTracker(color_preset="neon_green_orange")
    # Image with ONLY barrel marker (green)
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.circle(img, (280, 120), 15, (0, 255, 0), -1)

    hand_anchor = (0.20, 0.40)
    result = tracker.detect_in_image(img, hand_anchor=hand_anchor)
    assert result is not None
    handle, barrel, conf = result

    assert handle == hand_anchor
    assert math.isclose(barrel[0], 280 / 400, abs_tol=0.04)
    assert math.isclose(barrel[1], 120 / 300, abs_tol=0.04)
    assert conf >= 0.65


def test_color_marker_tracker_empty_image_returns_none() -> None:
    tracker = ColorMarkerBatTracker(color_preset="neon_green_orange")
    # Black empty image
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    result = tracker.detect_in_image(img)
    assert result is None


def test_color_marker_tracker_full_track(tmp_path: Path) -> None:
    tracker = ColorMarkerBatTracker(color_preset="neon_green_orange")

    # Generate 5 frame images in tmp_path
    for i in range(5):
        frame_img = _create_synthetic_marker_image(
            handle_pos=(100 + i * 10, 150),
            barrel_pos=(260 + i * 15, 140 - i * 5),
            handle_bgr=(0, 140, 255),
            barrel_bgr=(0, 255, 0),
        )
        cv2.imwrite(str(tmp_path / f"frame_{i:04d}.jpg"), frame_img)

    # Build movement mock
    movement = MovementRecording(
        recording_id="test-color-track",
        source_video_id="synth_vid",
        fps=30.0,
        quality_summary=PoseSequenceQuality(
            total_frames=5,
            frames_with_pose=5,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
        frames=[
            FramePose(
                frame_index=i,
                timestamp_seconds=i / 30.0,
                joints={
                    "left_wrist": JointObservation(
                        joint_name="left_wrist", x=0.25, y=0.5, confidence=0.9
                    ),
                    "right_wrist": JointObservation(
                        joint_name="right_wrist", x=0.25, y=0.5, confidence=0.9
                    ),
                },
            )
            for i in range(5)
        ],
    )

    result = tracker.track("synth_vid", frames_dir=tmp_path, movement=movement)
    assert isinstance(result, BatTrackingResult)
    assert result.total_frames == 5
    assert result.detected_frames_count == 5
    assert result.tracking_coverage == 1.0
    assert result.peak_barrel_speed is not None
    assert result.peak_barrel_speed > 0.0


def test_hybrid_bat_tracker_falls_back_when_no_markers(tmp_path: Path) -> None:
    hybrid = HybridBatTracker(color_preset="neon_green_orange", edge_fallback=True)

    # Generate plain black/gray frames without colored tape
    for i in range(4):
        plain_frame = np.zeros((300, 400, 3), dtype=np.uint8)
        # Add white line for edge detector
        cv2.line(plain_frame, (100, 150), (250, 150), (255, 255, 255), 4)
        cv2.imwrite(str(tmp_path / f"frame_{i:04d}.jpg"), plain_frame)

    movement = MovementRecording(
        recording_id="test-hybrid",
        source_video_id="hybrid_vid",
        fps=30.0,
        quality_summary=PoseSequenceQuality(
            total_frames=4,
            frames_with_pose=4,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
        frames=[
            FramePose(
                frame_index=i,
                timestamp_seconds=i / 30.0,
                joints={},
            )
            for i in range(4)
        ],
    )

    result = hybrid.track("hybrid_vid", frames_dir=tmp_path, movement=movement)
    assert isinstance(result, BatTrackingResult)
    # The hybrid tracker should gracefully execute and return results
    assert result.total_frames == 4


def test_api_pipeline_run_with_color_marker_parameters() -> None:
    client = TestClient(app)
    mock_pipeline_res = {
        "video_id": "test_marker_api",
        "source_fps": 30.0,
        "processing_fps": 30.0,
        "processing_mode": "full",
        "bat_tracking_mode": "color_markers",
        "marker_color_preset": "yellow_pink",
        "total_frames": 5,
        "batter_handedness": "RHB",
        "bat_trajectory_3d": [],
        "pose_3d_frames": [],
    }

    with patch("app.api.routes.pipeline.run_pipeline", return_value=mock_pipeline_res) as mock_run:
        response = client.post(
            "/api/v1/pipeline/run/test_marker_api",
            json={
                "bat_tracking_mode": "color_markers",
                "marker_color_preset": "yellow_pink",
                "processing_mode": "full",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "test_marker_api"
        assert data["bat_tracking_mode"] == "color_markers"
        assert data["marker_color_preset"] == "yellow_pink"
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["bat_tracking_mode"] == "color_markers"
        assert call_kwargs["marker_color_preset"] == "yellow_pink"

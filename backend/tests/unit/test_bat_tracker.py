from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from app.schemas.bat import BatDetection
from app.services.bat_tracker_service import ShaftEdgeBatTracker


def test_bat_tracker_angle_and_sweet_spot() -> None:
    tracker = ShaftEdgeBatTracker()
    handle = (0.2, 0.2)
    barrel = (0.6, 0.2)

    angle = tracker._calculate_angle_deg(handle, barrel)
    assert math.isclose(angle, 0.0, abs_tol=1e-3)

    sweet = tracker.compute_sweet_spot(handle, barrel, ratio=0.75)
    assert math.isclose(sweet[0], 0.5, abs_tol=1e-3)
    assert math.isclose(sweet[1], 0.2, abs_tol=1e-3)


def test_bat_tracker_detect_in_synthetic_image(tmp_path: Path) -> None:
    tracker = ShaftEdgeBatTracker(
        min_line_length_ratio=0.1,
        max_line_length_ratio=0.7,
        hough_threshold=15,
    )
    img_path = tmp_path / "synthetic_frame.jpg"

    # Draw a 400x400 black image with a thick white line representing bat shaft
    canvas = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.line(canvas, (100, 100), (300, 300), (255, 255, 255), 4)
    cv2.imwrite(str(img_path), canvas)

    result = tracker.detect_in_image(img_path)
    assert result is not None
    p1, p2, conf = result
    assert conf > 0.2
    # Diag in norm coords for (0.5, 0.5) delta is sqrt(0.5) ~ 0.707
    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    assert 0.3 < length < 0.85


def test_bat_tracker_trajectory_and_attack_angle() -> None:
    tracker = ShaftEdgeBatTracker()
    # Simulate a 3-frame sequence where the barrel moves up and forward (slight upward attack angle)
    detections = [
        BatDetection(
            frame_index=0,
            timestamp_seconds=0.0,
            detected=True,
            handle_point=(0.4, 0.6),
            barrel_point=(0.5, 0.6),
            shaft_orientation_deg=0.0,
        ),
        BatDetection(
            frame_index=1,
            timestamp_seconds=0.033,
            detected=True,
            handle_point=(0.42, 0.58),
            barrel_point=(0.6, 0.55),  # dx = +0.1, dy = -0.05 (upward)
            shaft_orientation_deg=10.0,
        ),
    ]

    traj = tracker._build_trajectory(detections)
    assert len(traj) == 2
    assert traj[1].barrel_speed is not None
    assert traj[1].barrel_speed > 0.0
    assert traj[1].angular_velocity_deg_s is not None
    assert traj[1].angular_velocity_deg_s > 0.0

    # Test attack angle
    attack = tracker._calculate_attack_angle(traj, contact_frame=1)
    assert attack is not None
    # dx=0.1, dy_upward = 0.05 -> atan2(0.05, 0.1) ~ 26.56 deg
    assert 20.0 < attack < 35.0


def test_bat_tracker_gap_interpolation() -> None:
    tracker = ShaftEdgeBatTracker()
    # Frame 0 detected, Frame 1 missing, Frame 2 detected
    detections = [
        BatDetection(
            frame_index=0,
            timestamp_seconds=0.0,
            detected=True,
            handle_point=(0.2, 0.4),
            barrel_point=(0.4, 0.4),
            confidence=0.8,
        ),
        BatDetection(
            frame_index=1,
            timestamp_seconds=0.033,
            detected=False,
        ),
        BatDetection(
            frame_index=2,
            timestamp_seconds=0.066,
            detected=True,
            handle_point=(0.4, 0.4),
            barrel_point=(0.6, 0.4),
            confidence=0.8,
        ),
    ]

    tracker._interpolate_short_gaps(detections, max_gap=2)

    assert detections[1].detected is True
    assert detections[1].handle_point is not None
    assert math.isclose(detections[1].handle_point[0], 0.3, abs_tol=1e-3)
    assert detections[1].barrel_point is not None
    assert math.isclose(detections[1].barrel_point[0], 0.5, abs_tol=1e-3)


def test_bat_tracker_gap_interpolation_and_speed_calculation() -> None:
    tracker = ShaftEdgeBatTracker()
    detections = [
        BatDetection(
            frame_index=0,
            timestamp_seconds=0.0,
            detected=True,
            handle_point=(0.1, 0.5),
            barrel_point=(0.3, 0.5),
            confidence=0.9,
        ),
        BatDetection(
            frame_index=1,
            timestamp_seconds=0.033333,
            detected=False,
        ),
        BatDetection(
            frame_index=2,
            timestamp_seconds=0.066666,
            detected=True,
            handle_point=(0.3, 0.5),
            barrel_point=(0.5, 0.5),
            confidence=0.9,
        ),
    ]

    tracker._interpolate_short_gaps(detections, max_gap=3)
    assert detections[1].detected is True
    assert detections[1].barrel_point is not None
    assert math.isclose(detections[1].barrel_point[0], 0.4, abs_tol=1e-3)

    trajectory = tracker._build_trajectory(detections)
    assert len(trajectory) == 3
    assert trajectory[1].barrel_speed is not None
    assert trajectory[1].barrel_speed > 0.0
    assert trajectory[2].barrel_speed is not None
    assert trajectory[2].barrel_speed > 0.0

from __future__ import annotations

import math

from app.schemas.movement import (
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.schemas.segmentation import SwingWindow
from app.services.batting_metrics_service import BattingMetricsService


def _create_mock_pose_frame(
    frame_index: int,
    timestamp: float,
    *,
    sh_angle_rad: float = 0.0,
    hip_angle_rad: float = 0.0,
    wrist_x: float = 0.5,
    wrist_y: float = 0.5,
) -> FramePose:
    # Center around (0.5, 0.5)
    r_sh = 0.10
    r_hip = 0.08
    joints = {
        "left_shoulder": JointObservation(
            joint_name="left_shoulder",
            x=0.5 - r_sh * math.cos(sh_angle_rad),
            y=0.4 - r_sh * math.sin(sh_angle_rad),
            detected=True,
        ),
        "right_shoulder": JointObservation(
            joint_name="right_shoulder",
            x=0.5 + r_sh * math.cos(sh_angle_rad),
            y=0.4 + r_sh * math.sin(sh_angle_rad),
            detected=True,
        ),
        "left_hip": JointObservation(
            joint_name="left_hip",
            x=0.5 - r_hip * math.cos(hip_angle_rad),
            y=0.6 - r_hip * math.sin(hip_angle_rad),
            detected=True,
        ),
        "right_hip": JointObservation(
            joint_name="right_hip",
            x=0.5 + r_hip * math.cos(hip_angle_rad),
            y=0.6 + r_hip * math.sin(hip_angle_rad),
            detected=True,
        ),
        "right_wrist": JointObservation(
            joint_name="right_wrist",
            x=wrist_x,
            y=wrist_y,
            detected=True,
        ),
        "left_wrist": JointObservation(
            joint_name="left_wrist",
            x=wrist_x - 0.03,
            y=wrist_y,
            detected=True,
        ),
    }
    return FramePose(
        frame_index=frame_index,
        timestamp_seconds=timestamp,
        detected=True,
        joints=joints,
    )


def test_shoulder_hip_separation_calculation() -> None:
    # Frame with shoulders tilted at 30 deg, hips horizontal (0 deg) -> separation should be ~30 deg
    f1 = _create_mock_pose_frame(
        0, 0.0, sh_angle_rad=math.radians(30), hip_angle_rad=0.0
    )
    rec = MovementRecording(
        recording_id="sep-test",
        source_video_id="video-001",
        duration_seconds=0.1,
        frames=[f1],
        quality_summary=PoseSequenceQuality(
            total_frames=1,
            frames_with_pose=1,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )

    metrics = BattingMetricsService.analyze_batting_swing(rec)
    frame_m = metrics.frame_metrics[0]

    assert frame_m.shoulder_hip_separation_deg is not None
    assert math.isclose(frame_m.shoulder_hip_separation_deg, 30.0, abs_tol=1.0)


def test_kinematic_sequence_order_detection() -> None:
    # Build 5 frames:
    # Frame 1: hips move fast
    # Frame 2: shoulders move fast
    # Frame 3: hands move fast (contact)
    frames: list[FramePose] = []
    dt = 0.01

    for i in range(5):
        t = i * dt
        # Hips move mostly at frame 1
        hip_y = 0.6 + (0.05 if i == 1 else 0.0)
        # Shoulders move mostly at frame 2
        sh_y = 0.4 + (0.06 if i == 2 else 0.0)
        # Wrists move mostly at frame 3
        wrist_x = 0.3 + (0.15 if i >= 3 else 0.0)

        f = _create_mock_pose_frame(i, t, wrist_x=wrist_x)
        # override hip and shoulder position to simulate kinematic sequence peak
        f.joints["right_hip"].y = hip_y
        f.joints["right_shoulder"].y = sh_y
        frames.append(f)

    rec = MovementRecording(
        recording_id="seq-test",
        source_video_id="video-001",
        duration_seconds=4 * dt,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=5,
            frames_with_pose=5,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )

    window = SwingWindow(
        window_id=1,
        start_frame=0,
        end_frame=4,
        start_time_seconds=0.0,
        end_time_seconds=4 * dt,
        duration_seconds=4 * dt,
        peak_speed_frame=3,
        peak_speed_time_seconds=3 * dt,
        peak_hand_speed=15.0,
        contact_frame=3,
        contact_time_seconds=3 * dt,
    )

    result = BattingMetricsService.analyze_batting_swing(rec, swing_window=window)
    seq = result.kinematic_sequence

    assert seq.pelvis_peak is not None
    assert seq.torso_peak is not None
    assert seq.hands_peak is not None
    assert (
        seq.pelvis_peak.peak_frame_index
        <= seq.torso_peak.peak_frame_index
        <= seq.hands_peak.peak_frame_index
    )


def test_hand_path_cumulative_length() -> None:
    frames: list[FramePose] = [
        _create_mock_pose_frame(0, 0.00, wrist_x=0.20, wrist_y=0.50),
        _create_mock_pose_frame(1, 0.01, wrist_x=0.30, wrist_y=0.50),
        _create_mock_pose_frame(2, 0.02, wrist_x=0.45, wrist_y=0.50),
    ]
    rec = MovementRecording(
        recording_id="handpath-test",
        source_video_id="video-001",
        duration_seconds=0.02,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=3,
            frames_with_pose=3,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )
    window = SwingWindow(
        window_id=1,
        start_frame=0,
        end_frame=2,
        start_time_seconds=0.0,
        end_time_seconds=0.02,
        duration_seconds=0.02,
        peak_speed_frame=2,
        peak_speed_time_seconds=0.02,
        peak_hand_speed=15.0,
        contact_frame=2,
        contact_time_seconds=0.02,
    )
    result = BattingMetricsService.analyze_batting_swing(rec, swing_window=window)

    # Path from 0.20 -> 0.30 -> 0.45 = 0.10 + 0.15 = 0.25 total distance
    assert math.isclose(result.hand_path.hand_path_length, 0.25, abs_tol=0.01)

from __future__ import annotations

import math

from app.schemas.movement import (
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.schemas.pitching import PitchingPhaseType
from app.services.pitching_analyzer_service import PitchingAnalyzer


def _create_pitch_frame(
    frame_index: int,
    timestamp: float,
    *,
    r_wrist: tuple[float, float] = (0.5, 0.5),
    l_wrist: tuple[float, float] = (0.4, 0.5),
    r_elbow: tuple[float, float] = (0.55, 0.45),
    l_elbow: tuple[float, float] = (0.35, 0.45),
    r_shoulder: tuple[float, float] = (0.55, 0.35),
    l_shoulder: tuple[float, float] = (0.45, 0.35),
    r_hip: tuple[float, float] = (0.53, 0.55),
    l_hip: tuple[float, float] = (0.47, 0.55),
    r_knee: tuple[float, float] = (0.53, 0.70),
    l_knee: tuple[float, float] = (0.47, 0.70),
    r_ankle: tuple[float, float] = (0.53, 0.85),
    l_ankle: tuple[float, float] = (0.47, 0.85),
) -> FramePose:
    def make_joint(name: str, pt: tuple[float, float]) -> JointObservation:
        return JointObservation(joint_name=name, x=pt[0], y=pt[1], detected=True)

    joints = {
        "right_wrist": make_joint("right_wrist", r_wrist),
        "left_wrist": make_joint("left_wrist", l_wrist),
        "right_elbow": make_joint("right_elbow", r_elbow),
        "left_elbow": make_joint("left_elbow", l_elbow),
        "right_shoulder": make_joint("right_shoulder", r_shoulder),
        "left_shoulder": make_joint("left_shoulder", l_shoulder),
        "right_hip": make_joint("right_hip", r_hip),
        "left_hip": make_joint("left_hip", l_hip),
        "right_knee": make_joint("right_knee", r_knee),
        "left_knee": make_joint("left_knee", l_knee),
        "right_ankle": make_joint("right_ankle", r_ankle),
        "left_ankle": make_joint("left_ankle", l_ankle),
    }
    return FramePose(
        frame_index=frame_index,
        timestamp_seconds=timestamp,
        joints=joints,
    )


def test_pitching_analyzer_too_few_frames():
    analyzer = PitchingAnalyzer()
    movement = MovementRecording(
        recording_id="rec-pitch-001",
        source_video_id="pitch_short",
        duration_seconds=0.1,
        frames=[_create_pitch_frame(i, i / 30.0) for i in range(3)],
        quality_summary=PoseSequenceQuality(
            total_frames=3,
            frames_with_pose=3,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )
    result = analyzer.analyze_pitch(movement)
    assert not result.delivery_detected
    assert result.delivery_window is None


def test_pitching_analyzer_rhp_delivery():
    analyzer = PitchingAnalyzer()
    frames = []
    fps = 30.0
    total_frames = 20

    for i in range(total_frames):
        t = i / fps
        # Left knee lifts high at frame 5 (low y value in image coords)
        l_knee_y = 0.50 if i == 5 else 0.70

        # Right wrist accelerates to a sharp peak between frame 12 and 13 (release at 13)
        if i == 12:
            r_wrist_pos = (0.50, 0.40)
        elif i == 13:
            r_wrist_pos = (0.75, 0.30)  # Large displacement -> high speed
        else:
            r_wrist_pos = (0.50 + 0.005 * i, 0.45)

        # Foot strike around frame 9: lead ankle strides forward
        l_ankle_pos = (0.35, 0.85) if i >= 9 else (0.47, 0.85)
        r_ankle_pos = (0.55, 0.85)

        frame = _create_pitch_frame(
            frame_index=i,
            timestamp=t,
            r_wrist=r_wrist_pos,
            l_knee=(0.47, l_knee_y),
            l_ankle=l_ankle_pos,
            r_ankle=r_ankle_pos,
        )
        frames.append(frame)

    movement = MovementRecording(
        recording_id="rec-pitch-rhp",
        source_video_id="rhp_fastball",
        duration_seconds=total_frames / fps,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=total_frames,
            frames_with_pose=total_frames,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )

    result = analyzer.analyze_pitch(movement)
    assert result.delivery_detected
    assert result.delivery_window is not None
    assert result.delivery_window.release_frame == 13
    assert result.delivery_window.leg_lift_frame == 5
    assert result.delivery_window.foot_strike_frame == 9

    # Verify handedness
    assert result.metrics is not None
    assert result.metrics.handedness == "RHP"

    # Verify stride length
    expected_stride = math.hypot(0.35 - 0.55, 0.85 - 0.85)
    assert result.metrics.stride_length_normalized is not None
    assert abs(result.metrics.stride_length_normalized - expected_stride) < 1e-4

    # Verify knee angles and arm slot
    assert result.metrics.lead_knee_angle_at_foot_strike is not None
    assert result.metrics.lead_knee_angle_at_release is not None
    assert result.metrics.arm_slot_angle_deg is not None
    assert result.metrics.elbow_flexion_at_foot_strike_deg is not None
    assert result.metrics.release_height_normalized is not None
    assert result.metrics.is_proximal_to_distal

    # Verify temporal phases
    phase_names = [p.phase_name for p in result.delivery_window.phases]
    assert PitchingPhaseType.LEG_LIFT in phase_names
    assert PitchingPhaseType.STRIDE in phase_names
    assert PitchingPhaseType.RELEASE in phase_names


def test_pitching_analyzer_lhp_detection_and_override():
    analyzer = PitchingAnalyzer()
    frames = []
    fps = 30.0

    for i in range(20):
        t = i / fps
        # Left wrist has dramatic movement (LHP pitcher)
        l_wrist_pos = (0.20, 0.20) if i == 14 else (0.40, 0.40)
        r_wrist_pos = (0.60, 0.40)

        # Right knee lifts for LHP
        r_knee_y = 0.48 if i == 6 else 0.70

        frames.append(
            _create_pitch_frame(
                frame_index=i,
                timestamp=t,
                l_wrist=l_wrist_pos,
                r_wrist=r_wrist_pos,
                r_knee=(0.53, r_knee_y),
            )
        )

    movement = MovementRecording(
        recording_id="rec-pitch-lhp",
        source_video_id="lhp_curve",
        duration_seconds=20 / fps,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=20,
            frames_with_pose=20,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )

    result_lhp = analyzer.analyze_pitch(movement)
    assert result_lhp.metrics is not None
    assert result_lhp.metrics.handedness == "LHP"

    # With override
    result_override = analyzer.analyze_pitch(movement, handedness_override="RHP")
    assert result_override.metrics is not None
    assert result_override.metrics.handedness == "RHP"

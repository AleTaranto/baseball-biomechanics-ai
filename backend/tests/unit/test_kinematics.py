from __future__ import annotations

from math import isclose

import pytest
from app.schemas.kinematics import KinematicRecording
from app.schemas.movement import (
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.services.kinematics_service import KinematicAnalysisService


@pytest.fixture
def base_quality() -> PoseSequenceQuality:
    return PoseSequenceQuality(
        total_frames=1,
        frames_with_pose=1,
        frames_without_pose=0,
        missing_joint_counts=0,
        low_confidence_joint_counts=0,
        temporal_continuity_status="continuous",
    )


def _make_joint(
    x: float,
    y: float,
    confidence: float = 0.9,
    visibility: float | None = None,
) -> JointObservation:
    return JointObservation(
        joint_name="joint",
        x=x,
        y=y,
        confidence=confidence,
        visibility=visibility if visibility is not None else confidence,
        detected=True,
    )


def test_elbow_angle_calculation_is_correct(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="kinematic-angle-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.0, 0.0),
                    "left_elbow": _make_joint(1.0, 0.0),
                    "left_wrist": _make_joint(1.0, 1.0),
                    "right_shoulder": _make_joint(0.1, 0.1),
                    "right_elbow": _make_joint(0.2, 0.1),
                    "right_wrist": _make_joint(0.2, 0.2),
                    "left_hip": _make_joint(0.2, 0.2),
                    "right_hip": _make_joint(0.3, 0.2),
                    "left_knee": _make_joint(0.2, 0.5),
                    "right_knee": _make_joint(0.3, 0.5),
                    "left_ankle": _make_joint(0.2, 0.8),
                    "right_ankle": _make_joint(0.3, 0.8),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    angle = result.frames[0].joint_angles["left_elbow_angle"]
    assert angle.valid is True
    assert angle.value_degrees is not None
    assert isclose(angle.value_degrees, 90.0, abs_tol=1e-6)


def test_knee_angle_calculation_is_correct(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="kinematic-knee-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.0, 0.0),
                    "left_elbow": _make_joint(0.2, 0.1),
                    "left_wrist": _make_joint(0.2, 0.2),
                    "right_shoulder": _make_joint(0.8, 0.0),
                    "right_elbow": _make_joint(0.7, 0.1),
                    "right_wrist": _make_joint(0.7, 0.2),
                    "left_hip": _make_joint(0.0, 0.0),
                    "right_hip": _make_joint(1.0, 0.0),
                    "left_knee": _make_joint(1.0, 0.0),
                    "right_knee": _make_joint(0.7, 0.0),
                    "left_ankle": _make_joint(1.0, 1.0),
                    "right_ankle": _make_joint(0.7, 1.0),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    angle = result.frames[0].joint_angles["left_knee_angle"]
    assert angle.valid is True
    assert angle.value_degrees is not None
    assert isclose(angle.value_degrees, 90.0, abs_tol=1e-6)


def test_segment_vector_calculation_returns_expected_values(
    base_quality: PoseSequenceQuality,
) -> None:
    recording = MovementRecording(
        recording_id="segment-vector-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.0, 0.0),
                    "left_elbow": _make_joint(0.3, 0.4),
                    "left_wrist": _make_joint(0.3, 0.4),
                    "right_shoulder": _make_joint(0.1, 0.1),
                    "right_elbow": _make_joint(0.2, 0.1),
                    "right_wrist": _make_joint(0.2, 0.2),
                    "left_hip": _make_joint(0.2, 0.2),
                    "right_hip": _make_joint(0.3, 0.2),
                    "left_knee": _make_joint(0.2, 0.5),
                    "right_knee": _make_joint(0.3, 0.5),
                    "left_ankle": _make_joint(0.2, 0.8),
                    "right_ankle": _make_joint(0.3, 0.8),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    vector = result.frames[0].segment_vectors["left_upper_arm"]
    assert vector.valid is True
    assert vector.vector == {"x": 0.3, "y": 0.4}
    assert vector.magnitude is not None
    assert isclose(vector.magnitude, 0.5, abs_tol=1e-6)
    assert isclose(vector.normalized_vector["x"], 0.6, abs_tol=1e-6)
    assert isclose(vector.normalized_vector["y"], 0.8, abs_tol=1e-6)


def test_linear_velocity_uses_timestamp_delta(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="velocity-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=2.0,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.1, 0.1),
                    "left_elbow": _make_joint(0.2, 0.1),
                    "left_wrist": _make_joint(0.5, 0.1),
                    "right_shoulder": _make_joint(0.2, 0.2),
                    "right_elbow": _make_joint(0.3, 0.2),
                    "right_wrist": _make_joint(0.4, 0.2),
                    "left_hip": _make_joint(0.3, 0.3),
                    "right_hip": _make_joint(0.4, 0.3),
                    "left_knee": _make_joint(0.3, 0.5),
                    "right_knee": _make_joint(0.4, 0.5),
                    "left_ankle": _make_joint(0.3, 0.7),
                    "right_ankle": _make_joint(0.4, 0.7),
                },
            ),
            FramePose(
                frame_index=1,
                timestamp_seconds=1.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.2, 0.1),
                    "left_elbow": _make_joint(0.3, 0.1),
                    "left_wrist": _make_joint(0.9, 0.1),
                    "right_shoulder": _make_joint(0.2, 0.2),
                    "right_elbow": _make_joint(0.3, 0.2),
                    "right_wrist": _make_joint(0.4, 0.2),
                    "left_hip": _make_joint(0.3, 0.3),
                    "right_hip": _make_joint(0.4, 0.3),
                    "left_knee": _make_joint(0.3, 0.5),
                    "right_knee": _make_joint(0.4, 0.5),
                    "left_ankle": _make_joint(0.3, 0.7),
                    "right_ankle": _make_joint(0.4, 0.7),
                },
            ),
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    velocity = result.frames[1].linear_velocities["left_wrist"]
    assert velocity.valid is True
    assert velocity.value_normalized_units_per_second is not None
    assert velocity.value_normalized_units_per_second > 0.0


def test_first_frame_has_invalid_velocity(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="first-frame-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.1, 0.2),
                    "left_elbow": _make_joint(0.2, 0.3),
                    "left_wrist": _make_joint(0.3, 0.4),
                    "right_shoulder": _make_joint(0.4, 0.2),
                    "right_elbow": _make_joint(0.5, 0.3),
                    "right_wrist": _make_joint(0.6, 0.4),
                    "left_hip": _make_joint(0.1, 0.5),
                    "right_hip": _make_joint(0.6, 0.5),
                    "left_knee": _make_joint(0.2, 0.7),
                    "right_knee": _make_joint(0.5, 0.7),
                    "left_ankle": _make_joint(0.2, 0.9),
                    "right_ankle": _make_joint(0.5, 0.9),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    assert result.frames[0].linear_velocities["left_wrist"].valid is False
    assert result.frames[0].linear_velocities["left_wrist"].reason == "no_previous_frame"


def test_zero_time_delta_invalidates_velocity(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="zero-delta-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.1, 0.2),
                    "left_elbow": _make_joint(0.2, 0.3),
                    "left_wrist": _make_joint(0.3, 0.4),
                    "right_shoulder": _make_joint(0.4, 0.2),
                    "right_elbow": _make_joint(0.5, 0.3),
                    "right_wrist": _make_joint(0.6, 0.4),
                    "left_hip": _make_joint(0.1, 0.5),
                    "right_hip": _make_joint(0.6, 0.5),
                    "left_knee": _make_joint(0.2, 0.7),
                    "right_knee": _make_joint(0.5, 0.7),
                    "left_ankle": _make_joint(0.2, 0.9),
                    "right_ankle": _make_joint(0.5, 0.9),
                },
            ),
            FramePose(
                frame_index=1,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.2, 0.2),
                    "left_elbow": _make_joint(0.3, 0.3),
                    "left_wrist": _make_joint(0.4, 0.4),
                    "right_shoulder": _make_joint(0.5, 0.2),
                    "right_elbow": _make_joint(0.6, 0.3),
                    "right_wrist": _make_joint(0.7, 0.4),
                    "left_hip": _make_joint(0.1, 0.6),
                    "right_hip": _make_joint(0.6, 0.6),
                    "left_knee": _make_joint(0.2, 0.8),
                    "right_knee": _make_joint(0.5, 0.8),
                    "left_ankle": _make_joint(0.2, 1.0),
                    "right_ankle": _make_joint(0.5, 1.0),
                },
            ),
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    assert result.frames[1].linear_velocities["left_wrist"].valid is False
    assert result.frames[1].linear_velocities["left_wrist"].reason == "zero_or_negative_time_delta"


def test_missing_joint_invalidates_angle(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="missing-joint-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.0, 0.0),
                    "left_elbow": _make_joint(1.0, 0.0),
                    "right_shoulder": _make_joint(0.1, 0.1),
                    "right_elbow": _make_joint(0.2, 0.1),
                    "right_wrist": _make_joint(0.2, 0.2),
                    "left_hip": _make_joint(0.2, 0.2),
                    "right_hip": _make_joint(0.3, 0.2),
                    "left_knee": _make_joint(0.2, 0.5),
                    "right_knee": _make_joint(0.3, 0.5),
                    "left_ankle": _make_joint(0.2, 0.8),
                    "right_ankle": _make_joint(0.3, 0.8),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    assert result.frames[0].joint_angles["left_elbow_angle"].valid is False
    assert result.frames[0].joint_angles["left_elbow_angle"].reason == "missing_joint"


def test_low_confidence_input_invalidates_metric(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="low-confidence-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.0, 0.0, confidence=0.1),
                    "left_elbow": _make_joint(1.0, 0.0, confidence=0.2),
                    "left_wrist": _make_joint(1.0, 1.0, confidence=0.1),
                    "right_shoulder": _make_joint(0.1, 0.1),
                    "right_elbow": _make_joint(0.2, 0.1),
                    "right_wrist": _make_joint(0.2, 0.2),
                    "left_hip": _make_joint(0.2, 0.2),
                    "right_hip": _make_joint(0.3, 0.2),
                    "left_knee": _make_joint(0.2, 0.5),
                    "right_knee": _make_joint(0.3, 0.5),
                    "left_ankle": _make_joint(0.2, 0.8),
                    "right_ankle": _make_joint(0.3, 0.8),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    metric = result.frames[0].joint_angles["left_elbow_angle"]
    assert metric.valid is False
    assert metric.reason == "low_confidence_input"


def test_invalid_metrics_are_explicitly_marked(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="invalid-metric-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.0, 0.0),
                    "left_elbow": _make_joint(1.0, 0.0),
                    "left_wrist": _make_joint(1.0, 0.0),
                    "right_shoulder": _make_joint(0.1, 0.1),
                    "right_elbow": _make_joint(0.2, 0.1),
                    "right_wrist": _make_joint(0.2, 0.2),
                    "left_hip": _make_joint(0.2, 0.2),
                    "right_hip": _make_joint(0.3, 0.2),
                    "left_knee": _make_joint(0.2, 0.5),
                    "right_knee": _make_joint(0.3, 0.5),
                    "left_ankle": _make_joint(0.2, 0.8),
                    "right_ankle": _make_joint(0.3, 0.8),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    assert result.frames[0].joint_angles["left_elbow_angle"].valid is False
    assert result.frames[0].joint_angles["left_elbow_angle"].reason == "zero_length_segment"


def test_kinematic_recording_serializes_as_expected(base_quality: PoseSequenceQuality) -> None:
    recording = MovementRecording(
        recording_id="serialization-test",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.033,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(0.0, 0.0),
                    "left_elbow": _make_joint(1.0, 0.0),
                    "left_wrist": _make_joint(1.0, 1.0),
                    "right_shoulder": _make_joint(0.1, 0.1),
                    "right_elbow": _make_joint(0.2, 0.1),
                    "right_wrist": _make_joint(0.2, 0.2),
                    "left_hip": _make_joint(0.2, 0.2),
                    "right_hip": _make_joint(0.3, 0.2),
                    "left_knee": _make_joint(0.2, 0.5),
                    "right_knee": _make_joint(0.3, 0.5),
                    "left_ankle": _make_joint(0.2, 0.8),
                    "right_ankle": _make_joint(0.3, 0.8),
                },
            )
        ],
        quality_summary=base_quality,
    )

    result = KinematicAnalysisService().build_recording(recording)
    assert isinstance(result, KinematicRecording)
    assert result.source_recording_id == "serialization-test"
    assert "left_elbow_angle" in result.frames[0].joint_angles

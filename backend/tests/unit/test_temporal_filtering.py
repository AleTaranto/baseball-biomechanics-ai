from __future__ import annotations

import math

from app.schemas.movement import (
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.services.filtering_service import OneEuroFilter, TemporalFilteringService


def _create_mock_recording(
    frames_data: list[tuple[float, dict[str, tuple[float, float, float | None]]]],
) -> MovementRecording:
    """Helper to create a mock MovementRecording from (timestamp, {joint: (x, y, conf)})."""
    frames: list[FramePose] = []
    for idx, (t, joints_map) in enumerate(frames_data):
        joints: dict[str, JointObservation] = {}
        for name, (x, y, conf) in joints_map.items():
            joints[name] = JointObservation(
                joint_name=name,
                x=x,
                y=y,
                confidence=conf,
                detected=True,
            )
        frames.append(
            FramePose(
                frame_index=idx,
                timestamp_seconds=t,
                detected=True,
                joints=joints,
            )
        )

    return MovementRecording(
        recording_id="test-recording",
        source_video_id="test-video",
        fps=120.0,
        duration_seconds=frames[-1].timestamp_seconds if frames else 0.0,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=len(frames),
            frames_with_pose=len(frames),
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )


def test_one_euro_filter_reduces_stationary_jitter() -> None:
    f = OneEuroFilter(min_cutoff=1.0, beta=0.01, d_cutoff=1.0)
    # Simulate a stationary hand around x=0.5 with high-frequency jitter +/- 0.02
    t = 0.0
    dt = 1.0 / 120.0
    raw_jitter: list[float] = []
    filtered_values: list[float] = []

    for i in range(60):
        val = 0.5 + (0.02 if i % 2 == 0 else -0.02)
        raw_jitter.append(val)
        filtered = f.filter(val, t)
        filtered_values.append(filtered)
        t += dt

    # Filtered variance should be significantly lower than raw jitter
    raw_var = sum((v - 0.5) ** 2 for v in raw_jitter) / len(raw_jitter)
    filtered_var = sum((v - 0.5) ** 2 for v in filtered_values[10:]) / len(filtered_values[10:])
    assert filtered_var < raw_var * 0.3


def test_one_euro_filter_preserves_fast_swing_trajectory() -> None:
    # High-speed baseball movement: rapid trajectory transition
    f = OneEuroFilter(min_cutoff=1.0, beta=3.0, d_cutoff=1.0)
    t = 0.0
    dt = 1.0 / 120.0
    # Simulate a fast swing movement from x=0.2 to x=0.8 in 0.1s
    filtered_values: list[float] = []
    ground_truth: list[float] = []

    for i in range(30):
        x = 0.2 + (0.6 * (i / 30.0))
        ground_truth.append(x)
        filtered = f.filter(x, t)
        filtered_values.append(filtered)
        t += dt

    # At fast speeds, the adaptive cutoff should track very closely with minimal lag
    final_error = abs(filtered_values[-1] - ground_truth[-1])
    assert final_error < 0.03


def test_temporal_filtering_service_preserves_raw_data() -> None:
    service = TemporalFilteringService()
    frames_data: list[tuple[float, dict[str, tuple[float, float, float | None]]]] = [
        (0.0, {"left_wrist": (0.50, 0.50, 0.9)}),
        (0.01, {"left_wrist": (0.52, 0.51, 0.9)}),
        (0.02, {"left_wrist": (0.51, 0.49, 0.9)}),
    ]
    recording = _create_mock_recording(frames_data)
    filtered_rec = service.filter_recording(recording)

    assert filtered_rec.filter_status == "filtered"
    for orig_frame, filt_frame in zip(recording.frames, filtered_rec.frames):
        orig_joint = orig_frame.joints["left_wrist"]
        filt_joint = filt_frame.joints["left_wrist"]

        assert filt_joint.filtered is True
        assert filt_joint.raw_x == orig_joint.x
        assert filt_joint.raw_y == orig_joint.y
        # Values should be smoothed
        assert math.isclose(filt_joint.x, orig_joint.x, abs_tol=0.05)


def test_temporal_filtering_interpolates_short_gap() -> None:
    service = TemporalFilteringService(max_gap_frames=3)
    frames_data: list[tuple[float, dict[str, tuple[float, float, float | None]]]] = [
        (0.00, {"left_wrist": (0.10, 0.20, 0.9)}),
        (0.01, {}),  # gap frame 1
        (0.02, {}),  # gap frame 2
        (0.03, {"left_wrist": (0.40, 0.50, 0.9)}),
    ]
    recording = _create_mock_recording(frames_data)
    filtered_rec = service.filter_recording(recording, interpolate_gaps=True)

    # Frame 1 and 2 should now have interpolated joint
    j1 = filtered_rec.frames[1].joints.get("left_wrist")
    j2 = filtered_rec.frames[2].joints.get("left_wrist")

    assert j1 is not None and j1.interpolated is True
    assert j2 is not None and j2.interpolated is True
    assert 0.10 < j1.x < 0.40
    assert 0.10 < j2.x < 0.40
    assert j1.x < j2.x


def test_temporal_filtering_does_not_interpolate_long_gap() -> None:
    service = TemporalFilteringService(max_gap_frames=2)
    frames_data: list[tuple[float, dict[str, tuple[float, float, float | None]]]] = [
        (0.00, {"left_wrist": (0.10, 0.20, 0.9)}),
        (0.01, {}),
        (0.02, {}),
        (0.03, {}),  # 3 frames missing > max_gap_frames (2)
        (0.04, {"left_wrist": (0.50, 0.60, 0.9)}),
    ]
    recording = _create_mock_recording(frames_data)
    filtered_rec = service.filter_recording(recording, interpolate_gaps=True)

    assert "left_wrist" not in filtered_rec.frames[1].joints
    assert "left_wrist" not in filtered_rec.frames[2].joints
    assert "left_wrist" not in filtered_rec.frames[3].joints


def test_outlier_rejection_flags_impossible_teleportation() -> None:
    service = TemporalFilteringService(max_velocity_threshold=10.0)
    # dt = 0.01s. Jump of 0.8 distance in 0.01s is speed=80.0, clearly an outlier
    frames_data: list[tuple[float, dict[str, tuple[float, float, float | None]]]] = [
        (0.00, {"left_wrist": (0.10, 0.10, 0.9)}),
        (0.01, {"left_wrist": (0.90, 0.90, 0.9)}),  # outlier jump
        (0.02, {"left_wrist": (0.12, 0.11, 0.9)}),
    ]
    recording = _create_mock_recording(frames_data)
    filtered_rec = service.filter_recording(recording, reject_outliers=True, interpolate_gaps=True)

    # Frame 1 should have been flagged as outlier and reconstructed via interpolation
    j1 = filtered_rec.frames[1].joints["left_wrist"]
    assert j1.raw_x == 0.90
    assert j1.interpolated is True
    # The filtered x coordinate should be close to 0.11, not 0.90
    assert abs(j1.x - 0.11) < 0.05

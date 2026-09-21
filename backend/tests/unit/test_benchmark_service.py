from __future__ import annotations

import math
from pathlib import Path

from app.schemas.contact import ContactDetectionResult
from app.schemas.movement import (
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.services.benchmark_service import BenchmarkService


def test_evaluate_accuracy_calculation() -> None:
    frames = [
        FramePose(
            frame_index=0,
            timestamp_seconds=0.0,
            detected=True,
            joints={
                "right_wrist": JointObservation(
                    joint_name="right_wrist",
                    x=0.5,
                    y=0.5,
                    confidence=0.90,
                    detected=True,
                ),
                "left_wrist": JointObservation(
                    joint_name="left_wrist",
                    x=None,
                    y=None,
                    confidence=0.0,
                    detected=False,
                ),
            },
        ),
        FramePose(
            frame_index=1,
            timestamp_seconds=0.033,
            detected=True,
            joints={
                "right_wrist": JointObservation(
                    joint_name="right_wrist",
                    x=0.52,
                    y=0.51,
                    confidence=0.80,
                    detected=True,
                ),
            },
        ),
    ]
    movement = MovementRecording(
        recording_id="bench-rec",
        source_video_id="bench-vid",
        fps=30.0,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=2,
            frames_with_pose=2,
            frames_without_pose=0,
            missing_joint_counts=1,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )
    contact_res = ContactDetectionResult(
        video_id="bench-vid",
        contact_frame=10,
        contact_time_seconds=0.333,
        confidence=0.8,
    )

    acc = BenchmarkService.evaluate_accuracy(
        movement=movement,
        contact_result=contact_res,
        ground_truth_contact_frame=12,
    )

    assert acc.contact_frame_delta == 2
    assert acc.contact_time_error_ms is not None
    assert math.isclose(acc.contact_time_error_ms, (2 / 30.0) * 1000.0, abs_tol=1e-1)
    assert acc.tracking_failure_rate == 0.0
    assert 0.0 < acc.missing_keypoint_rate < 1.0


def test_run_benchmark_comparison_mock_runner(tmp_path: Path) -> None:
    dummy_video = tmp_path / "swing_sample.mp4"
    dummy_video.write_bytes(b"dummy")

    def mock_runner(*args, **kwargs) -> dict:
        mode = kwargs.get("processing_mode", "full")
        return {
            "video_id": "test-vid",
            "source_fps": 60.0,
            "total_frames": 60,
            "contact_frame": 30,
            "processing_mode": mode,
        }

    report = BenchmarkService.run_benchmark_on_video(
        video_path=dummy_video,
        pipeline_runner=mock_runner,
        strategies=["full", "half_rate", "two_pass"],
        ground_truth_contact=30,
        output_dir=tmp_path / "out",
    )

    assert report.dataset_name == "swing_sample"
    assert len(report.runs) == 3
    assert (tmp_path / "out" / "swing_sample_benchmark.json").exists()
    for run in report.runs:
        assert run.accuracy.contact_frame_delta == 0

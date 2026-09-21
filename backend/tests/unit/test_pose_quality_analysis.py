from __future__ import annotations

import json
from pathlib import Path

from app.schemas.movement import (
    DEFAULT_JOINTS,
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.services.pose_quality_service import PoseQualityAnalysisService


def _build_recording(frame_count: int = 3) -> MovementRecording:
    frames: list[FramePose] = []
    for index in range(frame_count):
        joints: dict[str, JointObservation] = {}
        for joint_name in DEFAULT_JOINTS:
            if index == 1 and joint_name == "left_knee":
                joints[joint_name] = JointObservation(
                    joint_name=joint_name,
                    x=0.1,
                    y=0.1,
                    confidence=0.1,
                    visibility=0.1,
                    detected=False,
                )
            else:
                joints[joint_name] = JointObservation(
                    joint_name=joint_name,
                    x=float(index) / 10.0,
                    y=0.3 + float(index) / 20.0,
                    confidence=0.9,
                    visibility=0.9,
                    detected=True,
                )
        frames.append(
            FramePose(
                frame_index=index,
                timestamp_seconds=float(index) * 0.033,
                detected=True,
                joints=joints,
            )
        )
    return MovementRecording(
        recording_id="synthetic-quality-test",
        source_video_id="synthetic-video",
        fps=30.0,
        duration_seconds=float(frame_count - 1) * 0.033,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=frame_count,
            frames_with_pose=frame_count,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="ok",
        ),
    )


def test_pose_quality_report_detects_missing_and_low_confidence_joints() -> None:
    recording = _build_recording(3)
    report = PoseQualityAnalysisService().analyze_recording(recording)

    assert "left_knee" in report.joint_quality
    assert report.temporal_quality["left_knee"].missing_detection_frame_indices == [1]
    assert report.joint_quality["left_knee"].detection_rate < 1.0
    assert report.joint_quality["left_knee"].low_confidence_frames == 0


def test_pose_quality_report_flags_large_displacement_anomalies() -> None:
    frames = []
    for index in range(3):
        joints: dict[str, JointObservation] = {}
        for joint_name in DEFAULT_JOINTS:
            if joint_name == "left_wrist":
                x = 0.1 if index == 0 else 0.8 if index == 1 else 0.8
                y = 0.2 if index == 0 else 0.2 if index == 1 else 0.2
            else:
                x = 0.2
                y = 0.3
            joints[joint_name] = JointObservation(
                joint_name=joint_name,
                x=x,
                y=y,
                confidence=0.95,
                visibility=0.95,
                detected=True,
            )
        frames.append(
            FramePose(
                frame_index=index,
                timestamp_seconds=float(index) * 0.033,
                detected=True,
                joints=joints,
            )
        )

    recording = MovementRecording(
        recording_id="anomaly-suite",
        source_video_id="demo-video",
        fps=30.0,
        duration_seconds=0.066,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=3,
            frames_with_pose=3,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="ok",
        ),
    )

    report = PoseQualityAnalysisService().analyze_recording(recording)
    assert any(
        anomaly.anomaly_type == "large_displacement"
        for anomaly in report.potential_tracking_anomalies
    )


def test_pose_quality_service_generates_artifacts() -> None:
    recording = _build_recording(2)
    service = PoseQualityAnalysisService()
    output_dir = Path("sample-data/pose-quality/test-fixture")
    if output_dir.exists():
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
    output = service.generate_analysis_artifacts(
        movement_recording=recording,
        output_dir=output_dir,
    )

    assert output["quality_summary"].exists()
    assert output["joint_quality_csv"].exists()
    assert output["temporal_quality_csv"].exists()
    payload = json.loads(output["quality_summary"].read_text(encoding="utf-8"))
    assert payload["swing_id"] == "synthetic-quality-test"

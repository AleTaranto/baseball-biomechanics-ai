from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.schemas.movement import (
    DEFAULT_JOINTS,
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.schemas.pose import PoseEstimationResponse, PoseFrameResult, PoseKeypoint
from app.services.movement_service import MovementDataService, PoseSequenceValidator


@pytest.fixture
def sample_pose_response() -> PoseEstimationResponse:
    frames = [
        PoseFrameResult(
            frame_index=0,
            timestamp_ms=0,
            detected=True,
            keypoints={
                name: PoseKeypoint(
                    name=name,
                    x=0.1,
                    y=0.2,
                    z=0.0,
                    visibility=0.9,
                    confidence=0.9,
                    detected=True,
                )
                for name in DEFAULT_JOINTS
            },
        ),
        PoseFrameResult(
            frame_index=1,
            timestamp_ms=33,
            detected=False,
            keypoints={
                name: PoseKeypoint(
                    name=name,
                    x=None,
                    y=None,
                    z=None,
                    visibility=0.0,
                    confidence=0.0,
                    detected=False,
                )
                for name in DEFAULT_JOINTS
            },
        ),
    ]
    return PoseEstimationResponse(
        video_id="demo-video",
        video_filename="demo-video.mp4",
        provider="mock",
        model_name="mock-model",
        frame_directory="sample-data/frames/demo-video",
        manifest_path="sample-data/pose-estimation/demo-video/manifest.json",
        total_frames=2,
        processed_frames=2,
        detected_frames=1,
        missing_frames=1,
        generated_at=datetime.now(UTC),
        frames=frames,
    )


def test_movement_mapper_converts_provider_format_to_recording(
    sample_pose_response: PoseEstimationResponse,
) -> None:
    recording = MovementDataService().build_recording(sample_pose_response, fps=30.0)

    assert recording.source_video_id == "demo-video"
    assert recording.fps == 30.0
    assert len(recording.frames) == 2
    assert recording.frames[0].frame_index == 0
    assert recording.frames[0].timestamp == 0
    assert recording.frames[0].joints["left_shoulder"].x == 0.1
    assert recording.frames[1].detected is False
    assert recording.quality_summary.frames_without_pose == 1


def test_validator_flags_missing_frames_and_timestamp_order() -> None:
    recording = MovementRecording(
        recording_id="bad-sequence",
        source_video_id="demo-video",
        fps=30.0,
        duration=100,
        frames=[
            FramePose(
                frame_index=0,
                timestamp=0,
                detected=True,
                joints={
                    "left_shoulder": JointObservation(
                        joint_name="left_shoulder",
                        x=0.1,
                        y=0.2,
                        confidence=0.8,
                        visibility=0.8,
                    ),
                    "right_shoulder": JointObservation(
                        joint_name="right_shoulder",
                        x=0.2,
                        y=0.3,
                        confidence=0.8,
                        visibility=0.8,
                    ),
                },
            ),
            FramePose(
                frame_index=2,
                timestamp=90,
                detected=True,
                joints={
                    "left_shoulder": JointObservation(
                        joint_name="left_shoulder",
                        x=0.3,
                        y=0.4,
                        confidence=0.9,
                        visibility=0.9,
                    )
                },
            ),
            FramePose(
                frame_index=3,
                timestamp=40,
                detected=True,
                joints={
                    "left_shoulder": JointObservation(
                        joint_name="left_shoulder",
                        x=0.4,
                        y=0.5,
                        confidence=0.9,
                        visibility=0.9,
                    )
                },
            ),
        ],
        quality_summary=PoseSequenceQuality(
            total_frames=3,
            frames_with_pose=3,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="pending",
        ),
    )

    result = PoseSequenceValidator().validate(recording)
    codes = {issue.code for issue in result.issues}

    assert "missing-frame" in codes
    assert "timestamp-order" in codes
    assert result.quality_summary.temporal_continuity_status == "warning"


def test_validator_flags_missing_joints_low_confidence_and_invalid_coordinates() -> None:
    recording = MovementRecording(
        recording_id="low-quality",
        source_video_id="demo-video",
        fps=30.0,
        duration=33,
        frames=[
            FramePose(
                frame_index=0,
                timestamp=0,
                detected=True,
                joints={
                    "left_shoulder": JointObservation(
                        joint_name="left_shoulder",
                        x=0.2,
                        y=0.4,
                        confidence=0.1,
                        visibility=0.1,
                    ),
                    "right_shoulder": JointObservation(
                        joint_name="right_shoulder",
                        x=1.5,
                        y=0.3,
                        confidence=0.9,
                        visibility=0.9,
                    ),
                },
            )
        ],
        quality_summary=PoseSequenceQuality(
            total_frames=1,
            frames_with_pose=1,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="pending",
        ),
    )

    result = PoseSequenceValidator().validate(recording)
    codes = {issue.code for issue in result.issues}

    assert "missing-joint" in codes
    assert "invalid-coordinate" in codes
    assert "low-confidence" in codes
    assert result.quality_summary.low_confidence_joint_counts >= 1


def test_quality_summary_is_continuous_for_clean_sequence() -> None:
    frames = [
        FramePose(
            frame_index=index,
            timestamp=index * 33,
            detected=True,
            joints={
                joint_name: JointObservation(
                    joint_name=joint_name,
                    x=0.2,
                    y=0.4,
                    confidence=0.95,
                    visibility=0.9,
                )
                for joint_name in DEFAULT_JOINTS
            },
        )
        for index in range(3)
    ]
    recording = MovementRecording(
        recording_id="clean-sequence",
        source_video_id="demo-video",
        fps=30.0,
        duration=66,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=3,
            frames_with_pose=3,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="pending",
        ),
    )

    result = PoseSequenceValidator().validate(recording)

    assert result.quality_summary.total_frames == 3
    assert result.quality_summary.frames_with_pose == 3
    assert result.quality_summary.frames_without_pose == 0
    assert result.quality_summary.temporal_continuity_status == "continuous"
    assert result.issues == []

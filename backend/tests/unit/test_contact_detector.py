from __future__ import annotations

from app.schemas.bat import BatTrackingResult
from app.schemas.movement import (
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.schemas.segmentation import SwingSegmentationResult, SwingWindow
from app.services.contact_detector_service import ContactEventDetector


def _make_dummy_movement(num_frames: int = 10) -> MovementRecording:
    frames = []
    for i in range(num_frames):
        frames.append(
            FramePose(
                frame_index=i,
                timestamp_seconds=float(i) * 0.033,
                joints={
                    "right_wrist": JointObservation(
                        joint_name="right_wrist",
                        x=0.5,
                        y=0.5 + (0.1 if i == 5 else 0.0),
                        detected=True,
                    ),
                },
            )
        )
    return MovementRecording(
        recording_id="test-rec",
        source_video_id="video-123",
        fps=30.0,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=num_frames,
            frames_with_pose=num_frames,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )


def test_contact_detector_manual_override() -> None:
    movement = _make_dummy_movement()
    detector = ContactEventDetector()

    res = detector.detect_contact(
        video_id="video-123",
        movement=movement,
        manual_contact_frame=7,
    )

    assert res.contact_frame == 7
    assert res.is_manual_override is True
    assert res.confidence == 1.0
    assert len(res.signals) == 1
    assert res.signals[0].signal_name == "manual_override"


def test_contact_detector_multimodal_consensus() -> None:
    # Build 30 frames with wrist accelerating at frame 21
    frames = [
        FramePose(
            frame_index=i,
            timestamp_seconds=float(i) * 0.033,
            joints={
                "right_wrist": JointObservation(
                    joint_name="right_wrist",
                    x=0.5,
                    y=0.5 + (0.15 if i == 21 else 0.0),
                    detected=True,
                ),
            },
        )
        for i in range(30)
    ]
    movement = MovementRecording(
        recording_id="test-rec",
        source_video_id="video-123",
        fps=30.0,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=30,
            frames_with_pose=30,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )
    detector = ContactEventDetector()

    bat_tracking = BatTrackingResult(
        video_id="video-123",
        peak_barrel_speed_frame=20,
        tracking_coverage=1.0,
        attack_angle_at_contact_deg=12.0,
    )
    segmentation = SwingSegmentationResult(
        recording_id="test-rec",
        swing_detected=True,
        total_swings_found=1,
        candidate_swings=[
            SwingWindow(
                window_id=1,
                start_frame=10,
                end_frame=28,
                start_time_seconds=0.33,
                end_time_seconds=0.92,
                duration_seconds=0.59,
                peak_speed_frame=21,
                peak_speed_time_seconds=0.69,
                peak_hand_speed=1.5,
                contact_frame=21,
            )
        ],
    )

    res = detector.detect_contact(
        video_id="video-123",
        movement=movement,
        bat_tracking=bat_tracking,
        segmentation=segmentation,
    )

    assert res.is_manual_override is False
    assert 20 <= res.contact_frame <= 21
    assert res.confidence > 0.6
    assert len(res.signals) >= 2


def test_contact_detector_fallback_on_empty() -> None:
    # completely stationary wrist (no velocity spikes)
    frames = [
        FramePose(
            frame_index=i,
            timestamp_seconds=float(i) * 0.033,
            joints={
                "right_wrist": JointObservation(
                    joint_name="right_wrist",
                    x=0.5,
                    y=0.5,
                    detected=True,
                ),
            },
        )
        for i in range(10)
    ]
    movement = MovementRecording(
        recording_id="flat-rec",
        source_video_id="video-123",
        fps=30.0,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=10,
            frames_with_pose=10,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )
    detector = ContactEventDetector()

    res = detector.detect_contact(
        video_id="video-123",
        movement=movement,
    )

    assert res.is_manual_override is False
    assert res.contact_frame == 5  # mid index of 10 frames
    assert res.confidence == 0.0

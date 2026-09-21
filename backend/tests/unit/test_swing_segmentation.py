from __future__ import annotations

import math

from app.schemas.movement import (
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceQuality,
)
from app.schemas.segmentation import SwingPhaseType
from app.services.swing_segmentation_service import BattingSwingSegmenter


def _build_simulated_swing(
    peak_speed: float = 3.5,
    n_frames: int = 60,
    fps: float = 120.0,
) -> MovementRecording:
    """Build a synthetic swing recording where wrist speed creates a clean baseball swing curve."""
    frames: list[FramePose] = []
    dt = 1.0 / fps

    # Model a swing peaking around frame 30
    # frames 0..15: stance (x ~ 0.3)
    # frames 15..22: load (x moves back to 0.25)
    # frames 22..32: downswing (x accelerates forward from 0.25 to 0.70)
    # frames 32..45: follow-through (x wraps to 0.85 and decelerates)
    # frames 45..60: finish
    for i in range(n_frames):
        t = i * dt
        if i < 15:
            x = 0.30
        elif i < 22:
            x = 0.30 - 0.05 * ((i - 15) / 7.0)
        elif i < 32:
            progress = (i - 22) / 10.0
            x = 0.25 + 0.45 * (progress**2)  # accelerating
        elif i < 45:
            progress = (i - 32) / 13.0
            x = 0.70 + 0.15 * math.sin(progress * math.pi / 2.0)
        else:
            x = 0.85

        joints = {
            "right_wrist": JointObservation(
                joint_name="right_wrist",
                x=x,
                y=0.5,
                confidence=0.9,
                detected=True,
            ),
            "left_wrist": JointObservation(
                joint_name="left_wrist",
                x=x - 0.04,
                y=0.5,
                confidence=0.9,
                detected=True,
            ),
        }
        frames.append(
            FramePose(
                frame_index=i,
                timestamp_seconds=t,
                detected=True,
                joints=joints,
            )
        )

    return MovementRecording(
        recording_id="sim-swing-001",
        source_video_id="sim-video",
        fps=fps,
        duration_seconds=(n_frames - 1) * dt,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=n_frames,
            frames_with_pose=n_frames,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )


def test_batting_segmenter_detects_clean_swing() -> None:
    recording = _build_simulated_swing()
    segmenter = BattingSwingSegmenter(min_swing_speed=0.5)
    result = segmenter.segment(recording)

    assert result.swing_detected is True
    assert result.total_swings_found >= 1
    assert result.primary_swing is not None

    swing = result.primary_swing
    assert swing.start_frame < swing.peak_speed_frame < swing.end_frame
    assert swing.duration_seconds >= 0.10
    assert swing.peak_hand_speed > 1.0


def test_batting_segmenter_generates_phases_and_contact_event() -> None:
    recording = _build_simulated_swing()
    segmenter = BattingSwingSegmenter(min_swing_speed=0.5)
    result = segmenter.segment(recording)
    assert result.primary_swing is not None
    swing = result.primary_swing

    phase_types = [p.phase for p in swing.phases]
    assert SwingPhaseType.DOWNSWING in phase_types
    assert SwingPhaseType.FOLLOW_THROUGH in phase_types

    event_names = [e.name for e in swing.events]
    assert "peak_hand_speed" in event_names
    assert "contact" in event_names

    contact_event = next(e for e in swing.events if e.name == "contact")
    assert contact_event.frame_index == swing.contact_frame


def test_batting_segmenter_rejects_idle_motion() -> None:
    # Build recording where joints barely move (stationary batter)
    frames: list[FramePose] = [
        FramePose(
            frame_index=i,
            timestamp_seconds=i / 120.0,
            detected=True,
            joints={
                "right_wrist": JointObservation(
                    joint_name="right_wrist",
                    x=0.50,
                    y=0.50,
                    confidence=0.9,
                    detected=True,
                )
            },
        )
        for i in range(50)
    ]
    recording = MovementRecording(
        recording_id="idle-movement",
        source_video_id="idle-video",
        fps=120.0,
        duration_seconds=49 / 120.0,
        frames=frames,
        quality_summary=PoseSequenceQuality(
            total_frames=50,
            frames_with_pose=50,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="stable",
        ),
    )

    segmenter = BattingSwingSegmenter(min_swing_speed=0.6)
    result = segmenter.segment(recording)

    assert result.swing_detected is False
    assert result.total_swings_found == 0
    assert result.primary_swing is None

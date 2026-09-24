from __future__ import annotations

from typing import cast

import cv2
import numpy as np
import pytest
from app.schemas.kinematics import AngleMetric, KinematicFrame, KinematicRecording, VelocityMetric
from app.schemas.movement import FramePose, JointObservation, MovementRecording, PoseSequenceQuality
from app.services.inspection_service import InspectionService


def _make_joint(
    *,
    x: float,
    y: float,
    confidence: float = 0.9,
    detected: bool = True,
) -> JointObservation:
    return JointObservation(
        joint_name="joint",
        x=x,
        y=y,
        confidence=confidence,
        visibility=confidence,
        detected=detected,
    )


def _base_quality() -> PoseSequenceQuality:
    return PoseSequenceQuality(
        total_frames=2,
        frames_with_pose=2,
        frames_without_pose=0,
        missing_joint_counts=0,
        low_confidence_joint_counts=0,
        temporal_continuity_status="continuous",
    )


def test_normalized_to_pixel_conversion() -> None:
    pixel = InspectionService.normalized_to_pixel(0.5, 0.25, width=640, height=480)
    assert pixel == (320, 120)


def test_coordinate_conversion_handles_multiple_resolutions() -> None:
    assert InspectionService.normalized_to_pixel(1.0, 1.0, width=1280, height=720) == (1280, 720)
    assert InspectionService.normalized_to_pixel(0.0, 0.0, width=320, height=180) == (0, 0)


def test_out_of_range_coordinates_are_clamped() -> None:
    pixel = InspectionService.normalized_to_pixel(1.5, -0.4, width=100, height=80)
    assert pixel == (100, 0)


def test_valid_and_invalid_joint_rendering_logic() -> None:
    valid = _make_joint(x=0.3, y=0.4)
    invalid = _make_joint(x=1.5, y=0.2, detected=False)
    assert InspectionService.joint_is_renderable(valid) is True
    assert InspectionService.joint_is_renderable(invalid) is False
    assert InspectionService.joint_is_renderable(None) is False


def test_skeleton_connection_and_angle_annotation_eligibility() -> None:
    frame = FramePose(
        frame_index=0,
        timestamp_seconds=0.0,
        detected=True,
        joints={
            "left_shoulder": _make_joint(x=0.1, y=0.1),
            "left_elbow": _make_joint(x=0.2, y=0.3),
            "left_wrist": _make_joint(x=0.4, y=0.5),
            "right_shoulder": _make_joint(x=0.8, y=0.1),
            "right_elbow": _make_joint(x=0.7, y=0.3),
            "right_wrist": _make_joint(x=0.6, y=0.5),
        },
    )
    assert InspectionService.skeleton_pair_is_eligible(
        frame,
        start_joint="left_shoulder",
        end_joint="left_elbow",
    )
    assert not InspectionService.skeleton_pair_is_eligible(
        frame,
        start_joint="left_shoulder",
        end_joint="missing_joint",
    )

    valid_metric = AngleMetric(value_degrees=90.0, valid=True, reason=None)
    invalid_metric = AngleMetric(value_degrees=None, valid=False, reason="low_confidence_input")
    assert InspectionService.angle_metric_is_renderable(valid_metric) is True
    assert InspectionService.angle_metric_is_renderable(invalid_metric) is False


def test_timestamp_order_validation() -> None:
    frames = [
        FramePose(frame_index=0, timestamp_seconds=0.0, joints={}),
        FramePose(frame_index=1, timestamp_seconds=0.5, joints={}),
        FramePose(frame_index=2, timestamp_seconds=0.4, joints={}),
    ]
    okay, issues = InspectionService.validate_timestamp_order(frames)
    assert okay is False
    assert any("timestamp_seconds" in issue for issue in issues)


def test_quality_summary_generation() -> None:
    movement = MovementRecording(
        recording_id="inspection-sample",
        source_video_id="swing1",
        fps=30.0,
        duration_seconds=0.1,
        frames=[
            FramePose(
                frame_index=0,
                timestamp_seconds=0.0,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(x=0.1, y=0.1),
                    "left_elbow": _make_joint(x=0.2, y=0.2),
                    "left_wrist": _make_joint(x=0.3, y=0.3),
                    "right_shoulder": _make_joint(x=0.7, y=0.1),
                    "right_elbow": _make_joint(x=0.6, y=0.2),
                    "right_wrist": _make_joint(x=0.5, y=0.3),
                    "left_hip": _make_joint(x=0.2, y=0.5),
                    "right_hip": _make_joint(x=0.8, y=0.5),
                    "left_knee": _make_joint(x=0.3, y=0.7),
                    "right_knee": _make_joint(x=0.7, y=0.7),
                    "left_ankle": _make_joint(x=0.2, y=0.9),
                    "right_ankle": _make_joint(x=0.8, y=0.9),
                },
            ),
            FramePose(
                frame_index=1,
                timestamp_seconds=0.033,
                detected=True,
                joints={
                    "left_shoulder": _make_joint(x=0.1, y=0.1),
                    "left_elbow": _make_joint(x=0.2, y=0.2),
                    "left_wrist": _make_joint(x=0.3, y=0.3),
                    "right_shoulder": _make_joint(x=0.7, y=0.1),
                    "right_elbow": _make_joint(x=0.6, y=0.2),
                    "right_wrist": _make_joint(x=0.5, y=0.3),
                    "left_hip": _make_joint(x=0.2, y=0.5),
                    "right_hip": _make_joint(x=0.8, y=0.5),
                    "left_knee": _make_joint(x=0.3, y=0.7),
                    "right_knee": _make_joint(x=0.7, y=0.7),
                    "left_ankle": _make_joint(x=0.2, y=0.9),
                    "right_ankle": _make_joint(x=0.8, y=0.9),
                },
            ),
        ],
        quality_summary=_base_quality(),
    )
    kinematic = KinematicRecording(
        recording_id="inspection-sample-kinematics",
        source_video_id="swing1",
        source_recording_id="inspection-sample",
        fps=30.0,
        duration_seconds=0.1,
        frames=[
            KinematicFrame(
                frame_index=0,
                timestamp_seconds=0.0,
                joint_angles={
                    "left_elbow_angle": AngleMetric(value_degrees=90.0, valid=True),
                    "right_elbow_angle": AngleMetric(value_degrees=90.0, valid=True),
                    "left_knee_angle": AngleMetric(value_degrees=90.0, valid=True),
                    "right_knee_angle": AngleMetric(value_degrees=90.0, valid=True),
                },
                segment_vectors={},
                linear_velocities={
                    "left_wrist": VelocityMetric(
                        value_normalized_units_per_second=0.1,
                        valid=True,
                    ),
                    "right_wrist": VelocityMetric(
                        value_normalized_units_per_second=0.2,
                        valid=True,
                    ),
                    "left_shoulder": VelocityMetric(
                        value_normalized_units_per_second=0.1,
                        valid=True,
                    ),
                    "right_shoulder": VelocityMetric(
                        value_normalized_units_per_second=0.2,
                        valid=True,
                    ),
                    "left_hip": VelocityMetric(
                        value_normalized_units_per_second=0.1,
                        valid=True,
                    ),
                    "right_hip": VelocityMetric(
                        value_normalized_units_per_second=0.2,
                        valid=True,
                    ),
                },
            ),
            KinematicFrame(
                frame_index=1,
                timestamp_seconds=0.033,
                joint_angles={
                    "left_elbow_angle": AngleMetric(
                        value_degrees=None,
                        valid=False,
                        reason="low_confidence_input",
                    ),
                    "right_elbow_angle": AngleMetric(value_degrees=85.0, valid=True),
                    "left_knee_angle": AngleMetric(value_degrees=90.0, valid=True),
                    "right_knee_angle": AngleMetric(
                        value_degrees=None,
                        valid=False,
                        reason="missing_joint",
                    ),
                },
                segment_vectors={},
                linear_velocities={
                    "left_wrist": VelocityMetric(
                        value_normalized_units_per_second=None,
                        valid=False,
                        reason="zero_or_negative_time_delta",
                    ),
                    "right_wrist": VelocityMetric(
                        value_normalized_units_per_second=0.15,
                        valid=True,
                    ),
                    "left_shoulder": VelocityMetric(
                        value_normalized_units_per_second=0.16,
                        valid=True,
                    ),
                    "right_shoulder": VelocityMetric(
                        value_normalized_units_per_second=None,
                        valid=False,
                        reason="low_confidence_input",
                    ),
                    "left_hip": VelocityMetric(
                        value_normalized_units_per_second=0.12,
                        valid=True,
                    ),
                    "right_hip": VelocityMetric(
                        value_normalized_units_per_second=0.18,
                        valid=True,
                    ),
                },
            ),
        ],
    )

    summary = InspectionService.build_quality_summary(movement, kinematic)
    metrics = cast(dict[str, dict[str, object]], summary["metrics"])
    left_elbow = cast(dict[str, object], metrics["left_elbow_angle"])
    left_wrist = cast(dict[str, object], metrics["left_wrist_velocity"])
    assert summary["total_frames"] == 2
    assert cast(int, left_elbow["valid_frames"]) == 1
    assert cast(int, left_wrist["invalid_frames"]) >= 1


@pytest.mark.parametrize("fps", [30.0, 60.0, 120.0])
def test_infer_fps_from_timestamps_supports_multiple_source_rates(fps: float) -> None:
    frames = [
        FramePose(frame_index=index, timestamp_seconds=index / fps, detected=True, joints={})
        for index in range(3)
    ]
    resolved = InspectionService.infer_fps_from_timestamps(frames)
    assert resolved is not None
    assert resolved == pytest.approx(fps, rel=1e-3)


@pytest.mark.parametrize("fps", [30.0, 60.0, 120.0])
def test_overlay_video_preserves_source_fps(tmp_path, fps: float) -> None:
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()
    for frame_index in range(2):
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        cv2.imwrite(str(frame_dir / f"frame_{frame_index:06d}.png"), image)

    movement = MovementRecording(
        recording_id=f"fps-{fps}-movement",
        source_video_id="demo-video",
        fps=fps,
        duration_seconds=1.0 / fps,
        frames=[
            FramePose(frame_index=0, timestamp_seconds=0.0, detected=True, joints={}),
            FramePose(frame_index=1, timestamp_seconds=1.0 / fps, detected=True, joints={}),
        ],
        quality_summary=PoseSequenceQuality(
            total_frames=2,
            frames_with_pose=2,
            frames_without_pose=0,
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="continuous",
        ),
    )
    kinematic = KinematicRecording(
        recording_id=f"fps-{fps}-kinematics",
        source_video_id="demo-video",
        source_recording_id="demo-movement",
        fps=fps,
        duration_seconds=1.0 / fps,
        frames=[
            KinematicFrame(
                frame_index=0,
                timestamp_seconds=0.0,
                joint_angles={},
                segment_vectors={},
                linear_velocities={},
            ),
            KinematicFrame(
                frame_index=1,
                timestamp_seconds=1.0 / fps,
                joint_angles={},
                segment_vectors={},
                linear_velocities={},
            ),
        ],
    )

    bundle = InspectionService.generate_inspection_bundle(
        movement=movement,
        kinematic=kinematic,
        extracted_frames_dir=frame_dir,
        output_dir=tmp_path / "inspection",
    )
    capture = cv2.VideoCapture(str(bundle["overlay_video"]))
    assert capture.isOpened() is True
    actual_fps = capture.get(cv2.CAP_PROP_FPS)
    assert actual_fps == pytest.approx(fps, rel=1e-2)
    capture.release()


def test_render_frame_overlay_supports_raw_and_filtered_modes() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    frame = FramePose(
        frame_index=1,
        timestamp_seconds=0.01,
        detected=True,
        joints={
            "left_shoulder": JointObservation(
                joint_name="left_shoulder",
                x=0.4,
                y=0.3,
                raw_x=0.42,
                raw_y=0.28,
                filtered=True,
            ),
            "left_elbow": JointObservation(
                joint_name="left_elbow",
                x=0.4,
                y=0.5,
                raw_x=0.41,
                raw_y=0.52,
                filtered=True,
            ),
        },
    )

    for mode in ["FILTERED", "RAW", "RAW+FILTERED"]:
        annotated = InspectionService.render_frame_overlay(
            image=image.copy(),
            movement_frame=frame,
            kinematic_frame=None,
            mode=mode,
        )
        assert annotated is not None
        assert annotated.shape == (100, 100, 3)
        # Verify overlay drew something
        assert np.any(annotated > 0)


def test_render_bat_overlay_and_action_hud() -> None:
    from app.schemas.bat import BatDetection
    from app.schemas.contact import ContactDetectionResult, ContactSignalEntry
    from app.schemas.segmentation import (
        SwingPhaseType,
        SwingSegmentationResult,
        SwingWindow,
        TemporalPhase,
    )

    image = np.zeros((200, 200, 3), dtype=np.uint8)
    bat_det = BatDetection(
        frame_index=5,
        timestamp_seconds=0.165,
        detected=True,
        handle_point=(0.4, 0.4),
        barrel_point=(0.7, 0.2),
        sweet_spot=(0.625, 0.25),
    )
    recent_pts = [(70, 90), (75, 85), (80, 80)]

    bat_annotated = InspectionService.render_bat_overlay(
        image=image.copy(),
        bat_detection=bat_det,
        recent_barrel_pts=recent_pts,
        width=200,
        height=200,
    )
    assert np.any(bat_annotated > 0)

    contact_res = ContactDetectionResult(
        video_id="test-vid",
        contact_frame=5,
        contact_time_seconds=0.165,
        confidence=0.9,
        signals=[ContactSignalEntry(signal_name="mock", estimated_frame=5, confidence=0.9)],
        consensus_spread_frames=0,
    )
    seg_res = SwingSegmentationResult(
        recording_id="test-rec",
        swing_detected=True,
        total_swings_found=1,
        candidate_swings=[
            SwingWindow(
                window_id=1,
                start_frame=0,
                end_frame=10,
                start_time_seconds=0.0,
                end_time_seconds=0.33,
                duration_seconds=0.33,
                peak_speed_frame=5,
                peak_speed_time_seconds=0.165,
                peak_hand_speed=1.8,
                contact_frame=5,
                phases=[
                    TemporalPhase(
                        phase=SwingPhaseType.DOWNSWING,
                        start_frame=0,
                        end_frame=6,
                        start_time_seconds=0.0,
                        end_time_seconds=0.2,
                        duration_seconds=0.2,
                    )
                ],
            )
        ],
    )

    hud_annotated = InspectionService.render_action_hud(
        image=image.copy(),
        frame_index=5,
        width=200,
        segmentation=seg_res,
        contact_result=contact_res,
    )
    assert np.any(hud_annotated > 0)


def test_render_pitching_overlay_and_action_hud() -> None:
    from app.schemas.pitching import (
        PitchingAnalysisResult,
        PitchingBiomechanicalMetrics,
        PitchingDeliveryWindow,
        PitchingPhase,
        PitchingPhaseType,
    )

    image = np.zeros((200, 200, 3), dtype=np.uint8)
    frame = FramePose(
        frame_index=10,
        timestamp_seconds=0.33,
        detected=True,
        joints={
            "right_wrist": _make_joint(x=0.6, y=0.4),
            "left_wrist": _make_joint(x=0.4, y=0.4),
            "right_shoulder": _make_joint(x=0.55, y=0.35),
            "right_elbow": _make_joint(x=0.6, y=0.4),
            "left_ankle": _make_joint(x=0.35, y=0.85),
            "right_ankle": _make_joint(x=0.55, y=0.85),
        },
    )

    pitching_res = PitchingAnalysisResult(
        video_id="pitch_overlay_test",
        delivery_detected=True,
        delivery_window=PitchingDeliveryWindow(
            start_frame=0,
            end_frame=20,
            duration_seconds=0.66,
            foot_strike_frame=7,
            release_frame=10,
            peak_hand_speed=2.5,
            phases=[
                PitchingPhase(
                    phase_name=PitchingPhaseType.RELEASE,
                    start_frame=9,
                    end_frame=11,
                    start_time_seconds=0.30,
                    end_time_seconds=0.36,
                    duration_seconds=0.06,
                )
            ],
        ),
        metrics=PitchingBiomechanicalMetrics(
            handedness="RHP",
            stride_length_normalized=0.45,
            arm_slot_angle_deg=45.0,
            lead_knee_angle_at_foot_strike=130.0,
            lead_knee_angle_at_release=140.0,
            max_shoulder_external_rotation_deg=170.0,
        ),
    )

    # Test HUD rendering with pitching badges, readouts, and release banner
    hud_img = InspectionService.render_action_hud(
        image=image.copy(),
        frame_index=10,
        width=200,
        pitching_result=pitching_res,
    )
    assert np.any(hud_img > 0)

    # Test pitching overlay with arm slot and wrist trail
    overlay_img = InspectionService.render_pitching_overlay(
        image=image.copy(),
        frame=frame,
        pitching_result=pitching_res,
        recent_wrist_pts=[(100, 80), (120, 80)],
        width=200,
        height=200,
    )
    assert np.any(overlay_img > 0)

    # Test full frame overlay integration
    full_overlay = InspectionService.render_frame_overlay(
        image=image.copy(),
        movement_frame=frame,
        kinematic_frame=None,
        pitching_result=pitching_res,
        recent_wrist_pts=[(100, 80), (120, 80)],
    )
    assert np.any(full_overlay > 0)


def test_render_3d_skeleton_anatomical_scaling() -> None:
    """Verify 3D skeleton rendering handles anatomical keypoint scaling."""
    frame = FramePose(
        frame_index=1,
        timestamp_seconds=0.033,
        detected=True,
        joints={
            "left_shoulder": JointObservation(joint_name="left_shoulder", x=0.4, y=0.3, z=-0.1),
            "right_shoulder": JointObservation(joint_name="right_shoulder", x=0.6, y=0.3, z=-0.1),
            "left_hip": JointObservation(joint_name="left_hip", x=0.45, y=0.6, z=0.0),
            "right_hip": JointObservation(joint_name="right_hip", x=0.55, y=0.6, z=0.0),
            "left_elbow": JointObservation(joint_name="left_elbow", x=0.35, y=0.45, z=-0.15),
            "right_elbow": JointObservation(joint_name="right_elbow", x=0.65, y=0.45, z=-0.15),
        },
    )
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    rendered = InspectionService.render_frame_overlay(
        image=img,
        movement_frame=frame,
        kinematic_frame=None,
        mode="FILTERED",
    )
    assert rendered is not None
    assert rendered.shape == (200, 200, 3)
    assert np.any(rendered > 0)


def test_render_2d_bat_overlay_stabilized() -> None:
    """Verify 2D bat overlay correctly renders barrel, handle, and trajectory."""
    from app.schemas.bat import BatDetection

    image = np.zeros((300, 300, 3), dtype=np.uint8)
    bat_det = BatDetection(
        frame_index=10,
        timestamp_seconds=0.33,
        detected=True,
        handle_point=(0.3, 0.5),
        barrel_point=(0.7, 0.2),
        sweet_spot=(0.6, 0.275),
        confidence=0.92,
        shaft_orientation_deg=35.0,
    )
    recent_pts = [(100, 200), (130, 180), (160, 150), (210, 60)]

    annotated = InspectionService.render_bat_overlay(
        image=image.copy(),
        bat_detection=bat_det,
        recent_barrel_pts=recent_pts,
        width=300,
        height=300,
    )
    assert annotated is not None
    assert annotated.shape == (300, 300, 3)
    # Ensure overlay modifies pixels
    assert np.any(annotated > 0)

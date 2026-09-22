from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.api.routes.analysis import _get_or_create_movement_and_kinematics
from app.schemas.kinematics import KinematicRecording
from app.schemas.movement import MovementRecording, PoseSequenceQuality
from fastapi import HTTPException


def test_get_or_create_movement_and_kinematics_existing(tmp_path: Path):
    video_id = "test_vid_exist"
    movement_dir = tmp_path / "sample-data" / "movement" / video_id
    kinematics_dir = tmp_path / "sample-data" / "kinematics" / video_id
    frames_dir = tmp_path / "sample-data" / "frames" / video_id

    movement_dir.mkdir(parents=True)
    kinematics_dir.mkdir(parents=True)
    frames_dir.mkdir(parents=True)

    dummy_quality = PoseSequenceQuality(
        total_frames=30,
        frames_with_pose=30,
        frames_without_pose=0,
        missing_joint_counts=0,
        low_confidence_joint_counts=0,
        temporal_continuity_status="ok",
    )
    dummy_movement = MovementRecording(
        recording_id=video_id,
        source_video_id=video_id,
        fps=30.0,
        duration_seconds=1.0,
        frames=[],
        quality_summary=dummy_quality,
    )
    dummy_kinematic = KinematicRecording(
        recording_id=f"{video_id}-kinematics",
        source_video_id=video_id,
        source_recording_id=video_id,
        fps=30.0,
        duration_seconds=1.0,
        frames=[],
    )

    (movement_dir / "movement_recording.json").write_text(
        json.dumps(dummy_movement.model_dump(mode="json")), encoding="utf-8"
    )
    (kinematics_dir / "kinematic_recording.json").write_text(
        json.dumps(dummy_kinematic.model_dump(mode="json")), encoding="utf-8"
    )

    with patch("app.api.routes.analysis.ROOT_DIR", tmp_path):
        m, k, f_dir = _get_or_create_movement_and_kinematics(video_id)
        assert m.source_video_id == video_id
        assert k.source_video_id == video_id
        assert f_dir == frames_dir


def test_get_or_create_movement_and_kinematics_generation(tmp_path: Path):
    video_id = "test_vid_gen"

    dummy_quality = PoseSequenceQuality(
        total_frames=0,
        frames_with_pose=0,
        frames_without_pose=0,
        missing_joint_counts=0,
        low_confidence_joint_counts=0,
        temporal_continuity_status="ok",
    )
    dummy_movement = MovementRecording(
        recording_id=video_id,
        source_video_id=video_id,
        fps=30.0,
        duration_seconds=1.0,
        frames=[],
        quality_summary=dummy_quality,
    )

    dummy_kinematic = KinematicRecording(
        recording_id=f"{video_id}-kinematics",
        source_video_id=video_id,
        source_recording_id=video_id,
        fps=30.0,
        duration_seconds=1.0,
        frames=[],
    )

    mock_pe_inst = MagicMock()
    with patch("app.api.routes.analysis.ROOT_DIR", tmp_path), patch(
        "app.services.frame_extraction_service.FrameExtractionService.extract_frames"
    ) as mock_fe, patch(
        "app.api.routes.analysis.PoseEstimationService",
        return_value=mock_pe_inst,
    ) as mock_pe_cls, patch(
        "app.services.movement_service.MovementDataMapper.from_pose_estimation_response",
        return_value=dummy_movement,
    ), patch(
        "app.services.filtering_service.TemporalFilteringService.filter_recording",
        return_value=dummy_movement,
    ), patch(
        "app.services.kinematics_service.KinematicAnalysisService.build_recording",
        return_value=dummy_kinematic,
    ):
        m, k, f_dir = _get_or_create_movement_and_kinematics(video_id)
        assert mock_fe.called
        assert mock_pe_cls.called
        assert mock_pe_inst.estimate_video.called
        assert m.source_video_id == video_id
        assert k.source_video_id == video_id
        assert f_dir == tmp_path / "sample-data" / "frames" / video_id


def test_get_or_create_movement_and_kinematics_extract_frames_failure(tmp_path: Path):
    video_id = "test_vid_fail"

    with patch("app.api.routes.analysis.ROOT_DIR", tmp_path), patch(
        "app.services.frame_extraction_service.FrameExtractionService.extract_frames",
        side_effect=RuntimeError("Video not found"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _get_or_create_movement_and_kinematics(video_id)
        assert exc_info.value.status_code == 404
        assert "Failed to find or extract frames" in exc_info.value.detail

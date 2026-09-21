from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.bat import BatTrackingResult
from app.schemas.batting import BattingMetricsResult
from app.schemas.contact import ContactDetectionResult
from app.schemas.kinematics import KinematicRecording
from app.schemas.movement import MovementRecording
from app.schemas.pitching import PitchingAnalysisResult
from app.services.bat_tracker_service import ShaftEdgeBatTracker
from app.services.batting_metrics_service import BattingMetricsService
from app.services.contact_detector_service import ContactEventDetector
from app.services.filtering_service import TemporalFilteringService
from app.services.frame_extraction_service import FrameExtractionService
from app.services.kinematics_service import KinematicAnalysisService
from app.services.movement_service import MovementDataMapper
from app.services.pitching_analyzer_service import PitchingAnalyzer
from app.services.pose_estimation_service import PoseEstimationService
from app.services.swing_segmentation_service import BattingSwingSegmenter

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
ROOT_DIR = Path(__file__).resolve().parents[4]


def _get_or_create_movement_and_kinematics(
    video_id: str,
) -> tuple[MovementRecording, KinematicRecording, Path]:
    movement_path = ROOT_DIR / "sample-data" / "movement" / video_id / "movement_recording.json"
    kinematics_path = (
        ROOT_DIR / "sample-data" / "kinematics" / video_id / "kinematic_recording.json"
    )
    frames_dir = ROOT_DIR / "sample-data" / "frames" / video_id

    if movement_path.exists() and kinematics_path.exists():
        movement = MovementRecording.model_validate_json(
            movement_path.read_text(encoding="utf-8")
        )
        kinematic = KinematicRecording.model_validate_json(
            kinematics_path.read_text(encoding="utf-8")
        )
        return movement, kinematic, frames_dir

    # Extract frames if necessary
    fe_service = FrameExtractionService()
    try:
        fe_service.extract_frames(video_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to find or extract frames for video '{video_id}': {exc}",
        ) from exc

    # Pose estimation
    pose_service = PoseEstimationService()
    pose_resp = pose_service.estimate_video(video_id=video_id)

    # Movement model & filtering
    raw_movement = MovementDataMapper.from_pose_estimation_response(
        pose_resp, recording_id=video_id
    )
    movement = TemporalFilteringService().filter_recording(raw_movement)
    movement_path.parent.mkdir(parents=True, exist_ok=True)
    movement_path.write_text(
        json.dumps(movement.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    # Kinematics
    kinematic = KinematicAnalysisService().build_recording(movement)
    kinematics_path.parent.mkdir(parents=True, exist_ok=True)
    kinematics_path.write_text(
        json.dumps(kinematic.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    return movement, kinematic, frames_dir


@router.post("/batting/{video_id}", response_model=BattingMetricsResult)
async def analyze_batting(
    video_id: str,
    manual_contact_frame: int | None = Query(
        None, description="Optional manual contact frame override."
    ),
) -> BattingMetricsResult:
    movement, kinematic, _ = _get_or_create_movement_and_kinematics(video_id)
    segmentation = BattingSwingSegmenter().segment(movement, kinematic)

    first_swing = (
        segmentation.candidate_swings[0] if segmentation.candidate_swings else None
    )
    metrics = BattingMetricsService().analyze_batting_swing(
        movement=movement,
        kinematic=kinematic,
        swing_window=first_swing,
    )

    out_path = ROOT_DIR / "sample-data" / "batting" / video_id / "batting_metrics.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(metrics.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return metrics


@router.post("/pitching/{video_id}", response_model=PitchingAnalysisResult)
async def analyze_pitching(
    video_id: str,
    handedness_override: str | None = Query(
        None, description="Optional pitcher handedness override: 'RHP' or 'LHP'."
    ),
) -> PitchingAnalysisResult:
    movement, kinematic, _ = _get_or_create_movement_and_kinematics(video_id)
    pitching_analyzer = PitchingAnalyzer()
    result = pitching_analyzer.analyze_pitch(
        movement=movement,
        kinematic=kinematic,
        handedness_override=handedness_override,
    )

    out_path = ROOT_DIR / "sample-data" / "pitching" / video_id / "pitching_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return result


@router.post("/bat-tracking/{video_id}", response_model=BatTrackingResult)
async def track_bat(video_id: str) -> BatTrackingResult:
    movement, _, frames_dir = _get_or_create_movement_and_kinematics(video_id)
    tracker = ShaftEdgeBatTracker()
    bat_result = tracker.track(
        video_id=video_id,
        frames_dir=frames_dir,
        movement=movement,
    )

    out_path = ROOT_DIR / "sample-data" / "bat-tracking" / video_id / "bat_tracking.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(bat_result.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return bat_result


@router.post("/contact/{video_id}", response_model=ContactDetectionResult)
async def detect_contact(
    video_id: str,
    manual_contact_frame: int | None = Query(
        None, description="Coach manual contact frame override."
    ),
) -> ContactDetectionResult:
    movement, kinematic, frames_dir = _get_or_create_movement_and_kinematics(video_id)
    segmentation = BattingSwingSegmenter().segment(movement, kinematic)

    tracker = ShaftEdgeBatTracker()
    bat_result = tracker.track(
        video_id=video_id,
        frames_dir=frames_dir,
        movement=movement,
    )

    detector = ContactEventDetector()
    contact_result = detector.detect_contact(
        video_id=video_id,
        movement=movement,
        bat_tracking=bat_result,
        segmentation=segmentation,
        kinematic=kinematic,
        manual_contact_frame=manual_contact_frame,
    )

    out_path = ROOT_DIR / "sample-data" / "contact" / video_id / "contact_events.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(contact_result.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return contact_result

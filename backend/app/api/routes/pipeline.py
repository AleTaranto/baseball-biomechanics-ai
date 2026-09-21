from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.pipeline import PipelineRunRequest, PipelineRunResponse
from app.schemas.two_pass import TwoPassConfig, TwoPassResult
from app.services.frame_extraction_service import FrameExtractionService
from app.services.two_pass_pipeline_service import TwoPassPipelineService

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run_pipeline import run_pipeline  # noqa: E402

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.post("/run/{video_id}", response_model=PipelineRunResponse)
async def execute_pipeline(
    video_id: str,
    request: PipelineRunRequest = PipelineRunRequest(),
) -> PipelineRunResponse:
    try:
        result = run_pipeline(
            video_id=video_id,
            processing_mode=request.processing_mode,
            sampling_interval=request.sampling_interval,
            filter_mode=request.filter_mode,
            generate_overlay=request.generate_overlay,
            manual_contact_frame=request.manual_contact_frame,
            handedness_override=request.handedness_override,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pipeline execution failed for video '{video_id}': {exc}",
        ) from exc

    return PipelineRunResponse(
        video_id=str(result["video_id"]),
        source_fps=result["source_fps"],  # type: ignore[arg-type]
        processing_fps=result["processing_fps"],  # type: ignore[arg-type]
        processing_mode=str(result["processing_mode"]),
        total_frames=int(result["total_frames"] or 0),
        frames_with_pose=int(result["frames_with_pose"] or 0),
        quality_summary_path=(
            str(result["quality_summary_path"])
            if result.get("quality_summary_path")
            else None
        ),
        overlay_video_path=(
            str(result["overlay_video_path"])
            if result.get("overlay_video_path")
            else None
        ),
        batting_metrics_path=(
            str(result["batting_metrics_path"])
            if result.get("batting_metrics_path")
            else None
        ),
        pitching_result_path=(
            str(result["pitching_result_path"])
            if result.get("pitching_result_path")
            else None
        ),
        contact_frame=result.get("contact_frame"),  # type: ignore[arg-type]
        contact_confidence=result.get("contact_confidence"),  # type: ignore[arg-type]
        peak_barrel_speed=result.get("peak_barrel_speed"),  # type: ignore[arg-type]
        max_shoulder_hip_separation_deg=result.get("max_shoulder_hip_separation_deg"),  # type: ignore[arg-type]
        stride_length_normalized=result.get("stride_length_normalized"),  # type: ignore[arg-type]
        arm_slot_angle_deg=result.get("arm_slot_angle_deg"),  # type: ignore[arg-type]
        compute_reduction_percentage=float(result.get("compute_reduction_percentage") or 0.0),
        action_windows_count=int(result.get("action_windows_count") or 0),
    )


@router.post("/two-pass/{video_id}", response_model=TwoPassResult)
async def execute_two_pass_scan(
    video_id: str,
    sampling_interval: int = Query(
        4, description="Coarse pass downsampled frame interval."
    ),
) -> TwoPassResult:
    fe = FrameExtractionService()
    frames_dir = ROOT_DIR / "sample-data" / "frames" / video_id
    if not frames_dir.exists():
        fe.extract_frames(video_id)

    config = TwoPassConfig(scan_sampling_interval=sampling_interval)
    windows = TwoPassPipelineService.scan_video_for_action_windows(
        frames_dir=frames_dir,
        fps=30.0,
        config=config,
    )
    total_f = len(list(frames_dir.glob("*.png")))
    return TwoPassPipelineService.evaluate_savings(
        video_id=video_id,
        total_frames=total_f,
        action_windows=windows,
        config=config,
    )

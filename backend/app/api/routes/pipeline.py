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

    def _to_int(val: object) -> int | None:
        if val is None or isinstance(val, (Path, dict, list)):
            return None
        if isinstance(val, (int, float, str, bytes, bytearray)):
            return int(val)
        return None

    def _to_float(val: object) -> float | None:
        if val is None or isinstance(val, (Path, dict, list)):
            return None
        if isinstance(val, (int, float, str, bytes, bytearray)):
            return float(val)
        return None

    return PipelineRunResponse(
        video_id=str(result.get("video_id", video_id)),
        source_fps=_to_float(result.get("source_fps")) or 0.0,
        processing_fps=_to_float(result.get("processing_fps")) or 0.0,
        processing_mode=str(result.get("processing_mode", request.processing_mode)),
        total_frames=_to_int(result.get("total_frames")) or 0,
        frames_with_pose=_to_int(result.get("frames_with_pose")) or 0,
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
        contact_frame=_to_int(result.get("contact_frame")),
        contact_confidence=_to_float(result.get("contact_confidence")),
        peak_barrel_speed=_to_float(result.get("peak_barrel_speed")),
        max_shoulder_hip_separation_deg=_to_float(result.get("max_shoulder_hip_separation_deg")),
        stride_length_normalized=_to_float(result.get("stride_length_normalized")),
        arm_slot_angle_deg=_to_float(result.get("arm_slot_angle_deg")),
        compute_reduction_percentage=_to_float(result.get("compute_reduction_percentage")) or 0.0,
        action_windows_count=_to_int(result.get("action_windows_count")) or 0,
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

    config = TwoPassConfig(scan_sampling_interval=sampling_interval, window_padding_seconds=0.5)
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

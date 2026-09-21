# ruff: noqa: E402
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.bat_tracker_service import ShaftEdgeBatTracker
from app.services.batting_metrics_service import BattingMetricsService
from app.services.contact_detector_service import ContactEventDetector
from app.services.filtering_service import TemporalFilteringService
from app.services.frame_extraction_service import FrameExtractionService
from app.services.inspection_service import InspectionService
from app.services.kinematics_service import KinematicAnalysisService
from app.services.movement_service import MovementDataService
from app.services.pose_estimation_service import PoseEstimationService
from app.services.pose_quality_service import PoseQualityAnalysisService
from app.services.profiling_service import PerformanceProfiler
from app.services.swing_segmentation_service import BattingSwingSegmenter
from app.services.two_pass_pipeline_service import TwoPassPipelineService
from app.services.video_ingestion_service import VideoIngestionService


class UploadStub:
    def __init__(self, *, filename: str, payload: bytes, content_type: str | None = None) -> None:
        self.filename = filename
        self.content_type = content_type or "application/octet-stream"
        self.file = io.BytesIO(payload)


def _resolve_sampling_interval(
    *,
    processing_mode: str,
    sampling_interval: int | None,
) -> int:
    if processing_mode in ("full", "two_pass"):
        return 1
    if processing_mode == "half_rate":
        return 2
    if processing_mode == "custom":
        if sampling_interval is None or sampling_interval <= 0:
            raise ValueError("A custom sampling interval must be a positive integer.")
        return int(sampling_interval)
    raise ValueError(f"Unsupported processing mode: {processing_mode!r}")


def run_pipeline(
    video_id: str | None = None,
    *,
    video_path: str | Path | None = None,
    fps: float | None = None,
    processing_mode: str = "full",
    sampling_interval: int | None = None,
    filter_mode: str = "filtered",
    generate_overlay: bool = True,
    manual_contact_frame: int | None = None,
    use_cache: bool = True,
    force_recompute: bool = False,
) -> dict[str, Path | str | int | float | None]:
    """Run the canonical pipeline with explicit processing-rate controls and profiling hooks."""
    if video_id is None and video_path is None:
        raise ValueError("Provide either a video_id or a video_path.")

    sampling_interval_value = _resolve_sampling_interval(
        processing_mode=processing_mode,
        sampling_interval=sampling_interval,
    )
    frame_manifest = None
    source_fps: float | None = None
    source_resolution: tuple[int, int] | None = None
    profiler = PerformanceProfiler()

    if video_path is not None:
        source = Path(video_path)
        if not source.exists():
            raise FileNotFoundError(f"Video file not found: {source}")
        if not source.is_file():
            raise ValueError(f"Path is not a file: {source}")

        payload = source.read_bytes()
        upload = UploadStub(
            filename=source.name,
            payload=payload,
            content_type=(
                "video/mp4"
                if source.suffix.lower() == ".mp4"
                else "application/octet-stream"
            ),
        )
        upload_response = VideoIngestionService().store_upload(cast(Any, upload))
        video_id = upload_response.id
        assert video_id is not None

        frame_manifest = profiler.profile_stage(
            "video_metadata_and_extraction",
            frames_processed=0,
            action=lambda: FrameExtractionService().extract_frames(video_id),
        )
        source_fps = frame_manifest.fps
        source_resolution = (
            (frame_manifest.width, frame_manifest.height)
            if frame_manifest.width and frame_manifest.height
            else None
        )
        selected_frames = list(frame_manifest.frames)[::sampling_interval_value]
        two_pass_result = None
        if processing_mode == "two_pass":
            extracted_dir = ROOT / "sample-data" / "frames" / str(video_id)
            if extracted_dir.exists():
                action_windows = profiler.profile_stage(
                    "two_pass_coarse_scan",
                    frames_processed=len(frame_manifest.frames),
                    input_fps=source_fps,
                    action=lambda: TwoPassPipelineService.scan_video_for_action_windows(
                        frames_dir=extracted_dir,
                        fps=source_fps or 30.0,
                    ),
                )
                two_pass_result = TwoPassPipelineService.evaluate_savings(
                    video_id=str(video_id),
                    total_frames=len(frame_manifest.frames),
                    action_windows=action_windows,
                )
                if action_windows:
                    active_indices = set()
                    for w in action_windows:
                        active_indices.update(range(w.start_frame, w.end_frame + 1))
                    selected_frames = [
                        f for f in frame_manifest.frames if f.frame_index in active_indices
                    ]

        profiler.report["source_fps"] = source_fps
        profiler.report["source_resolution"] = (
            list(source_resolution) if source_resolution is not None else None
        )
        profiler.report["total_frames"] = len(frame_manifest.frames)
        pose = profiler.profile_stage(
            "pose_estimation",
            frames_processed=len(selected_frames),
            input_fps=source_fps,
            input_resolution=source_resolution,
            action=lambda: PoseEstimationService().estimate_video(
                video_id,
                frame_entries=[
                    {
                        "frame_index": frame.frame_index,
                        "timestamp_ms": frame.timestamp_ms,
                        "relative_path": frame.relative_path,
                    }
                    for frame in selected_frames
                ],
                force=force_recompute,
            ),
        )
    else:
        if video_id is None:
            raise ValueError("A video_id is required when processing an existing manifest.")
        frame_manifest = profiler.profile_stage(
            "video_metadata_inspection",
            frames_processed=0,
            action=lambda: FrameExtractionService().load_manifest(video_id),
        )
        source_fps = frame_manifest.fps
        source_resolution = (
            (frame_manifest.width, frame_manifest.height)
            if frame_manifest.width and frame_manifest.height
            else None
        )
        selected_frames = list(frame_manifest.frames)[::sampling_interval_value]
        if use_cache:
            pose_path = (
                Path(__file__).resolve().parent
                / "sample-data"
                / "pose-estimation"
                / str(video_id)
                / "manifest.json"
            )
            if pose_path.exists() and not force_recompute:
                pose = profiler.profile_stage(
                    "pose_estimation_cache",
                    frames_processed=len(selected_frames),
                    action=lambda: PoseEstimationService().load_manifest(video_id),
                )
            else:
                pose = profiler.profile_stage(
                    "pose_estimation",
                    frames_processed=len(selected_frames),
                    input_fps=source_fps,
                    input_resolution=source_resolution,
                    action=lambda: PoseEstimationService().estimate_video(
                        video_id,
                        frame_entries=[
                            {
                                "frame_index": frame.frame_index,
                                "timestamp_ms": frame.timestamp_ms,
                                "relative_path": frame.relative_path,
                            }
                            for frame in selected_frames
                        ],
                        force=force_recompute,
                    ),
                )
        else:
            pose = profiler.profile_stage(
                "pose_estimation",
                frames_processed=len(selected_frames),
                input_fps=source_fps,
                input_resolution=source_resolution,
                action=lambda: PoseEstimationService().estimate_video(
                    video_id,
                    frame_entries=[
                        {
                            "frame_index": frame.frame_index,
                            "timestamp_ms": frame.timestamp_ms,
                            "relative_path": frame.relative_path,
                        }
                        for frame in selected_frames
                    ],
                    force=True,
                ),
            )

    effective_fps = fps if fps is not None and fps > 0 else source_fps
    if effective_fps is not None and sampling_interval_value > 1:
        effective_fps = effective_fps / sampling_interval_value

    movement_dir = ROOT / "sample-data" / "movement"
    movement_dir.mkdir(parents=True, exist_ok=True)
    movement_path = movement_dir / f"{video_id}.json"
    if use_cache and movement_path.exists() and not force_recompute:
        movement = profiler.profile_stage(
            "movement_loading",
            frames_processed=0,
            action=lambda: MovementDataService().load_recording(video_id),
        )
    else:
        movement = profiler.profile_stage(
            "movement_recording_generation",
            frames_processed=len(selected_frames),
            input_fps=source_fps,
            input_resolution=source_resolution,
            action=lambda: MovementDataService().build_recording(
                pose,
                recording_id=f"{video_id}-movement",
                fps=effective_fps,
            ),
        )
        movement_path.write_text(movement.model_dump_json(indent=2), encoding="utf-8")

    if filter_mode != "raw":
        movement = profiler.profile_stage(
            "temporal_filtering",
            frames_processed=len(movement.frames),
            input_fps=source_fps,
            action=lambda: TemporalFilteringService().filter_recording(movement),
        )

    validation = profiler.profile_stage(
        "validation",
        frames_processed=len(movement.frames),
        action=lambda: MovementDataService().validate_recording(movement),
    )
    kinematics_dir = ROOT / "sample-data" / "kinematics"
    kinematics_dir.mkdir(parents=True, exist_ok=True)
    kinematics_path = kinematics_dir / f"{video_id}.json"
    if use_cache and kinematics_path.exists() and not force_recompute:
        kinematics = profiler.profile_stage(
            "kinematic_loading",
            frames_processed=len(movement.frames),
            action=lambda: KinematicAnalysisService.load_recording(video_id),
        )
    else:
        kinematics = profiler.profile_stage(
            "kinematic_calculation",
            frames_processed=len(movement.frames),
            input_fps=source_fps,
            input_resolution=source_resolution,
            action=lambda: KinematicAnalysisService().build_recording(movement),
        )
        KinematicAnalysisService.persist_recording(kinematics, kinematics_dir)

    quality_dir = ROOT / "sample-data" / "pose-quality" / str(video_id)
    quality_result = profiler.profile_stage(
        "pose_quality_analysis",
        frames_processed=len(movement.frames),
        action=lambda: PoseQualityAnalysisService().generate_analysis_artifacts(
            movement_recording=movement,
            output_dir=quality_dir,
        ),
    )
    quality_summary = profiler.profile_stage(
        "quality_summary_generation",
        frames_processed=len(movement.frames),
        action=lambda: PoseQualityAnalysisService().analyze_recording(movement),
    )

    extracted_frames_dir = ROOT / "sample-data" / "frames" / str(video_id)

    segmentation_dir = ROOT / "sample-data" / "segmentation"
    segmentation_dir.mkdir(parents=True, exist_ok=True)
    segmentation_path = segmentation_dir / f"{video_id}.json"
    segmentation = profiler.profile_stage(
        "swing_segmentation",
        frames_processed=len(movement.frames),
        input_fps=source_fps,
        action=lambda: BattingSwingSegmenter().segment(movement=movement, kinematic=kinematics),
    )
    segmentation_path.write_text(segmentation.model_dump_json(indent=2), encoding="utf-8")

    batting_metrics_dir = ROOT / "sample-data" / "batting-metrics"
    batting_metrics_dir.mkdir(parents=True, exist_ok=True)
    batting_metrics_path = batting_metrics_dir / f"{video_id}.json"
    batting_metrics = profiler.profile_stage(
        "batting_metrics_analysis",
        frames_processed=len(movement.frames),
        input_fps=source_fps,
        action=lambda: BattingMetricsService().analyze(
            movement=movement,
            kinematic=kinematics,
            segmentation=segmentation,
        ),
    )
    batting_metrics_path.write_text(batting_metrics.model_dump_json(indent=2), encoding="utf-8")

    bat_tracking_dir = ROOT / "sample-data" / "bat-tracking"
    bat_tracking_dir.mkdir(parents=True, exist_ok=True)
    bat_tracking_path = bat_tracking_dir / f"{video_id}.json"
    bat_tracking = profiler.profile_stage(
        "bat_tracking",
        frames_processed=len(movement.frames),
        input_fps=source_fps,
        action=lambda: ShaftEdgeBatTracker().track(
            video_id=str(video_id),
            frames_dir=extracted_frames_dir,
            movement=movement,
        ),
    )
    bat_tracking_path.write_text(bat_tracking.model_dump_json(indent=2), encoding="utf-8")

    contact_events_dir = ROOT / "sample-data" / "contact-events"
    contact_events_dir.mkdir(parents=True, exist_ok=True)
    contact_events_path = contact_events_dir / f"{video_id}.json"
    contact_result = profiler.profile_stage(
        "contact_event_detection",
        frames_processed=len(movement.frames),
        input_fps=source_fps,
        action=lambda: ContactEventDetector().detect_contact(
            video_id=str(video_id),
            movement=movement,
            bat_tracking=bat_tracking,
            segmentation=segmentation,
            kinematic=kinematics,
            manual_contact_frame=manual_contact_frame,
        ),
    )
    contact_events_path.write_text(contact_result.model_dump_json(indent=2), encoding="utf-8")

    inspection_dir = ROOT / "sample-data" / "kinematic-inspection" / str(video_id)
    inspection_bundle = None
    overlay_mode = (
        "RAW+FILTERED"
        if filter_mode == "raw_plus_filtered"
        else ("RAW" if filter_mode == "raw" else "FILTERED")
    )
    if generate_overlay:
        inspection_bundle = profiler.profile_stage(
            "inspection_bundle_generation",
            frames_processed=len(movement.frames),
            action=lambda: InspectionService.generate_inspection_bundle(
                movement=movement,
                kinematic=kinematics,
                extracted_frames_dir=extracted_frames_dir,
                output_dir=inspection_dir,
                mode=overlay_mode,
                bat_tracking=bat_tracking,
                segmentation=segmentation,
                contact_result=contact_result,
                batting_metrics=batting_metrics,
            ),
        )

    profiler.write_report(ROOT / "sample-data" / "performance" / f"{video_id}.json")

    return {
        "video_id": video_id,
        "source_fps": source_fps,
        "processing_fps": effective_fps,
        "frame_sampling_interval": sampling_interval_value,
        "source_resolution": source_resolution,
        "movement_path": movement_path,
        "kinematics_path": kinematics_path,
        "segmentation_path": segmentation_path,
        "batting_metrics_path": batting_metrics_path,
        "bat_tracking_path": bat_tracking_path,
        "contact_events_path": contact_events_path,
        "contact_frame": contact_result.contact_frame,
        "contact_confidence": contact_result.confidence,
        "is_manual_contact_override": contact_result.is_manual_override,
        "bat_tracking_coverage": bat_tracking.tracking_coverage,
        "peak_barrel_speed": bat_tracking.peak_barrel_speed,
        "attack_angle_at_contact_deg": bat_tracking.attack_angle_at_contact_deg,
        "max_shoulder_hip_separation_deg": batting_metrics.max_shoulder_hip_separation_deg,
        "is_proximal_to_distal": (
            batting_metrics.kinematic_sequence.is_proximal_to_distal
            if batting_metrics.kinematic_sequence
            else None
        ),
        "swing_detected": segmentation.swing_detected,
        "total_swings_found": segmentation.total_swings_found,
        "quality_summary_path": quality_result["quality_summary"],
        "overlay_video_path": (
            inspection_bundle["overlay_video"] if inspection_bundle is not None else None
        ),
        "total_frames": len(movement.frames),
        "frames_with_pose": quality_summary.total_frames,
        "validation_issues": len(validation.issues),
        "processing_mode": processing_mode,
        "compute_reduction_percentage": (
            two_pass_result.compute_reduction_percentage
            if two_pass_result is not None
            else 0.0
        ),
        "action_windows_count": (
            len(two_pass_result.action_windows)
            if two_pass_result is not None
            else 0
        ),
        "filter_mode": filter_mode,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the full canonical pipeline for a known video id or a raw video file.",
    )
    parser.add_argument(
        "video_id",
        nargs="?",
        help="Video ID returned by the upload endpoint.",
    )
    parser.add_argument(
        "--video-path",
        type=str,
        help="Path to a raw video file to upload and process.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Optional override for source FPS. When omitted, the actual video metadata is used.",
    )
    parser.add_argument(
        "--processing-mode",
        choices=["full", "half_rate", "custom", "two_pass"],
        default="full",
        help="Processing mode: full, half_rate, custom, or two_pass coarse-scan ROI analysis.",
    )
    parser.add_argument(
        "--sampling-interval",
        type=int,
        default=1,
        help="Frame sampling interval for custom mode; ignored for full/half_rate.",
    )
    parser.add_argument(
        "--filter-mode",
        choices=["filtered", "raw", "raw_plus_filtered"],
        default="filtered",
        help="Temporal filtering mode: filtered (One-Euro), raw, or raw_plus_filtered overlay.",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Skip optional overlay generation for the final inspection bundle.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force recomputation instead of reusing canonical artifacts.",
    )
    parser.add_argument(
        "--manual-contact-frame",
        type=int,
        default=None,
        help="Explicitly override contact/impact frame.",
    )
    args = parser.parse_args()

    if not args.video_id and not args.video_path:
        parser.error("Either a video_id or --video-path is required.")

    result = run_pipeline(
        video_id=args.video_id,
        video_path=args.video_path,
        fps=args.fps,
        processing_mode=args.processing_mode,
        sampling_interval=args.sampling_interval,
        filter_mode=args.filter_mode,
        generate_overlay=not args.no_overlay,
        manual_contact_frame=args.manual_contact_frame,
        use_cache=not args.no_cache,
    )
    print(json.dumps({
        "video_id": result["video_id"],
        "source_fps": result["source_fps"],
        "processing_fps": result["processing_fps"],
        "frame_sampling_interval": result["frame_sampling_interval"],
        "movement_path": str(result["movement_path"]),
        "kinematics_path": str(result["kinematics_path"]),
        "quality_summary_path": str(result["quality_summary_path"]),
        "overlay_video_path": (
            str(result["overlay_video_path"])
            if result["overlay_video_path"] is not None
            else None
        ),
        "total_frames": result["total_frames"],
        "frames_with_pose": result["frames_with_pose"],
    }, indent=2))

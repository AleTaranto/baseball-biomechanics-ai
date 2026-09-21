from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.benchmark import BenchmarkComparisonReport
from app.services.benchmark_service import BenchmarkService
from app.services.frame_extraction_service import FrameExtractionService

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run_pipeline import run_pipeline  # noqa: E402

router = APIRouter(prefix="/api/v1/benchmark", tags=["benchmark"])


@router.post("/run/{video_id}", response_model=BenchmarkComparisonReport)
async def run_benchmark(
    video_id: str,
    ground_truth_contact: int | None = Query(
        None, description="Ground truth contact frame for accuracy comparison."
    ),
) -> BenchmarkComparisonReport:
    try:
        fe = FrameExtractionService()
        video_path, _ = fe._resolve_video_path(video_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file for '{video_id}' could not be located: {exc}",
        ) from exc

    report = BenchmarkService.run_benchmark_on_video(
        video_path=video_path,
        pipeline_runner=run_pipeline,
        strategies=["full", "half_rate", "two_pass"],
        ground_truth_contact=ground_truth_contact,
        output_dir=ROOT_DIR / "sample-data" / "benchmark",
    )
    return report

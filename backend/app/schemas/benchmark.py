from __future__ import annotations

from pydantic import BaseModel, Field


class AccuracyMetrics(BaseModel):
    """Ground truth comparison and kinematic precision metrics."""

    mean_pose_confidence: float = Field(..., description="Average landmark confidence score.")
    missing_keypoint_rate: float = Field(
        ..., description="Fraction of required keypoints that were undetected."
    )
    tracking_failure_rate: float = Field(
        ..., description="Fraction of video frames where tracking dropped."
    )
    contact_frame_delta: int | None = Field(
        None, description="Difference in frames compared to ground truth contact frame."
    )
    contact_time_error_ms: float | None = Field(
        None, description="Difference in milliseconds compared to ground truth contact time."
    )


class BenchmarkRunResult(BaseModel):
    """Execution performance and quality summary for a single benchmark run."""

    video_id: str
    processing_mode: str
    total_frames: int
    frames_processed: int
    elapsed_time_seconds: float
    effective_throughput_fps: float
    speedup_ratio: float = 1.0
    accuracy: AccuracyMetrics


class BenchmarkComparisonReport(BaseModel):
    """Comparative report across multiple pipeline strategies."""

    dataset_name: str
    runs: list[BenchmarkRunResult] = Field(default_factory=list)
    fastest_strategy: str = "full"
    recommended_production_strategy: str = "two_pass"

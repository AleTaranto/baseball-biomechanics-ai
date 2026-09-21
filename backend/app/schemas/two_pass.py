from __future__ import annotations

from pydantic import BaseModel, Field


class TwoPassConfig(BaseModel):
    """Configuration options for two-pass video processing."""

    scan_sampling_interval: int = Field(
        4,
        ge=2,
        description="Frame interval for Pass 1 coarse scanning (e.g. sample every 4th frame).",
    )
    window_padding_seconds: float = Field(
        0.3,
        ge=0.0,
        description="Temporal safety margin added before and after identified action windows.",
    )


class ActionWindow(BaseModel):
    """Temporal action segment identified during Pass 1 coarse scan."""

    start_frame: int
    end_frame: int
    start_time_seconds: float
    end_time_seconds: float
    action_type: str = "swing"
    motion_intensity: float = 0.0


class TwoPassResult(BaseModel):
    """Report comparing computation requirements between Full-Rate and Two-Pass execution."""

    video_id: str
    total_video_frames: int
    pass1_scanned_frames: int
    pass2_analyzed_frames: int
    total_processed_frames: int
    compute_reduction_percentage: float = Field(
        ...,
        description="Frame evaluation savings compared to naive 100% full-rate processing.",
    )
    action_windows: list[ActionWindow] = Field(default_factory=list)

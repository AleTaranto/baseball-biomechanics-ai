from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PoseKeypoint(BaseModel):
    name: str = Field(..., description="Body keypoint name.")
    x: float | None = Field(default=None, description="Normalized x coordinate in [0, 1].")
    y: float | None = Field(default=None, description="Normalized y coordinate in [0, 1].")
    z: float | None = Field(default=None, description="Normalized depth-like coordinate.")
    visibility: float | None = Field(
        default=None, description="Visibility score if the provider provides one."
    )
    confidence: float | None = Field(
        default=None, description="Confidence score when visibility is unavailable."
    )
    detected: bool = Field(default=True, description="Whether the keypoint was found.")


class PoseFrameResult(BaseModel):
    frame_index: int = Field(
        ..., ge=0, description="Frame index from the extraction stage."
    )
    timestamp_ms: int = Field(
        ..., ge=0, description="Timestamp in milliseconds for the frame."
    )
    detected: bool = Field(
        default=False,
        description="Whether at least one valid pose was detected for the frame.",
    )
    error: str | None = Field(
        default=None,
        description="Model or frame processing error if present.",
    )
    keypoints: dict[str, PoseKeypoint] = Field(
        default_factory=dict,
        description="Keypoints keyed by canonical body-part name.",
    )


class PoseEstimationResponse(BaseModel):
    video_id: str = Field(..., description="Identifier of the processed video.")
    video_filename: str = Field(..., description="Original stored video filename.")
    provider: str = Field(..., description="Concrete pose provider used for the run.")
    model_name: str = Field(..., description="Model deployed by the provider.")
    frame_directory: str = Field(..., description="Directory with extracted frames used as input.")
    manifest_path: str = Field(..., description="Path to the persisted pose manifest JSON.")
    total_frames: int = Field(..., ge=0, description="Total number of frames processed.")
    processed_frames: int = Field(..., ge=0, description="Frames attempted by the estimator.")
    detected_frames: int = Field(..., ge=0, description="Frames with at least one detected pose.")
    missing_frames: int = Field(..., ge=0, description="Frames without a detected pose.")
    generated_at: datetime = Field(..., description="Timestamp for the pose-estimation run.")
    frames: list[PoseFrameResult] = Field(
        default_factory=list, description="Per-frame pose payload in time order."
    )

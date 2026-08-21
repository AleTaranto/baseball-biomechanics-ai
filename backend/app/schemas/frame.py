from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VideoFrameMetadata(BaseModel):
    frame_index: int = Field(
        ..., ge=0, description="Sequential index of the frame in time order."
    )
    timestamp_ms: int = Field(
        ..., ge=0, description="Estimated timestamp for the frame in milliseconds."
    )
    file_name: str = Field(..., description="Filename of the saved frame image.")
    relative_path: str = Field(
        ..., description="Relative path from the repo root to the saved frame image."
    )
    width: int = Field(..., ge=1, description="Frame width in pixels.")
    height: int = Field(..., ge=1, description="Frame height in pixels.")


class FrameExtractionResponse(BaseModel):
    video_id: str = Field(..., description="Unique video identifier from ingestion metadata.")
    video_filename: str = Field(..., description="Stored video filename.")
    video_path: str = Field(..., description="Relative path of the source video on disk.")
    frame_directory: str = Field(
        ..., description="Relative folder where extracted frames are stored."
    )
    manifest_path: str = Field(
        ..., description="Relative path to the extracted-frame manifest JSON."
    )
    fps: float | None = Field(
        default=None, description="Detected video frame rate in frames per second."
    )
    total_frames: int = Field(
        ..., ge=0, description="Number of successfully extracted frames."
    )
    extracted_at: datetime = Field(
        ..., description="Time when the frame extraction run completed."
    )
    frames: list[VideoFrameMetadata] = Field(
        default_factory=list, description="Frame metadata ordered by time."
    )

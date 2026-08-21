from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VideoUploadResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for the uploaded video.")
    filename: str = Field(
        ..., description="Stored filename for the uploaded video."
    )
    original_filename: str = Field(
        ..., description="Original filename provided by the client."
    )
    content_type: str = Field(
        ..., description="Detected MIME type for the uploaded video."
    )
    size_bytes: int = Field(
        ..., ge=1, description="Uploaded file size in bytes."
    )
    saved_path: str = Field(
        ..., description="Relative path where the file was stored."
    )
    metadata_path: str = Field(
        ..., description="Relative path to the metadata record for the upload."
    )
    uploaded_at: datetime = Field(
        ..., description="Time at which the upload was received."
    )

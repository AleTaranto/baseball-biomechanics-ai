from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.video import VideoUploadResponse
from fastapi import UploadFile

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".m4v", ".wmv", ".webm"}


class VideoIngestionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root_dir = Path(__file__).resolve().parents[3]
        self.storage_dir = self.root_dir / self.settings.upload_dir
        self.max_upload_bytes = self.settings.max_upload_size_mb * 1024 * 1024

    def _validate_upload(
        self,
        filename: str | None,
        content_type: str | None,
        payload: bytes,
    ) -> None:
        if not filename:
            raise ValueError("A file name is required.")

        suffix = Path(filename).suffix.lower()
        is_valid_content_type = bool(content_type and content_type.startswith("video/"))
        if suffix not in ALLOWED_VIDEO_EXTENSIONS and not is_valid_content_type:
            raise ValueError(
                "Unsupported video format. Use one of: MP4, MOV, AVI, M4V, "
                "WMV, or WebM."
            )

        if not payload:
            raise ValueError("Uploaded file is empty.")

        if len(payload) > self.max_upload_bytes:
            raise ValueError(
                f"Uploaded file exceeds the maximum size of {self.settings.max_upload_size_mb} MB."
            )

    def store_upload(self, upload: UploadFile) -> VideoUploadResponse:
        if upload.file is None:
            raise ValueError("No file data was provided.")

        payload = upload.file.read()
        self._validate_upload(upload.filename, upload.content_type, payload)

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        video_id = str(uuid4())
        original_filename = upload.filename or "upload"
        suffix = Path(original_filename).suffix.lower() or ".mp4"
        stored_name = f"{video_id}{suffix}"
        stored_path = self.storage_dir / stored_name
        stored_path.write_bytes(payload)

        upload_timestamp = datetime.now(UTC)
        metadata_path = self.storage_dir / f"{video_id}.json"
        metadata = {
            "id": video_id,
            "filename": stored_name,
            "original_filename": original_filename,
            "content_type": upload.content_type or "application/octet-stream",
            "size_bytes": len(payload),
            "saved_path": str(Path(self.settings.upload_dir) / stored_name),
            "metadata_path": str(Path(self.settings.upload_dir) / metadata_path.name),
            "uploaded_at": upload_timestamp.isoformat(),
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return VideoUploadResponse(
            id=video_id,
            filename=stored_name,
            original_filename=original_filename,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(payload),
            saved_path=str(Path(self.settings.upload_dir) / stored_name),
            metadata_path=str(Path(self.settings.upload_dir) / metadata_path.name),
            uploaded_at=upload_timestamp,
        )

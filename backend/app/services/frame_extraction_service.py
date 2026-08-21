from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
from app.core.config import get_settings
from app.schemas.frame import FrameExtractionResponse, VideoFrameMetadata

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".m4v", ".wmv", ".webm"}


class FrameExtractionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root_dir = Path(__file__).resolve().parents[3]
        self.upload_dir = self.root_dir / self.settings.upload_dir
        self.frames_root = self.root_dir / "sample-data" / "frames"

    def _resolve_video_path(self, video_id: str) -> tuple[Path, str]:
        metadata_path = self.upload_dir / f"{video_id}.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            saved_path = metadata.get("saved_path")
            if saved_path:
                normalized_path = Path(str(saved_path).replace("\\", "/"))
                candidates: list[Path] = []
                if normalized_path.is_absolute():
                    candidates.append(normalized_path)
                else:
                    candidates.append(self.root_dir / normalized_path)
                    file_name = normalized_path.name
                    if file_name:
                        candidates.append(self.upload_dir / file_name)
                for candidate in candidates:
                    if candidate.exists():
                        return candidate, metadata.get("filename") or candidate.name

        matches = [
            candidate
            for candidate in self.upload_dir.glob(f"{video_id}.*")
            if candidate.suffix.lower() in ALLOWED_VIDEO_EXTENSIONS
        ]
        if matches:
            return matches[0], matches[0].name

        raise ValueError(f"No stored video was found for id '{video_id}'.")

    def load_manifest(self, video_id: str) -> FrameExtractionResponse:
        manifest_path = self.frames_root / video_id / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"No frame manifest exists for video id '{video_id}'.")

        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return FrameExtractionResponse.model_validate(payload)

    def extract_frames(self, video_id: str) -> FrameExtractionResponse:
        video_path, video_filename = self._resolve_video_path(video_id)
        if not video_path.exists():
            raise ValueError(f"The video file for id '{video_id}' does not exist on disk.")

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError(f"The video '{video_filename}' could not be opened or is corrupted.")

        try:
            fps: float | None = float(capture.get(cv2.CAP_PROP_FPS))
            if fps is not None and fps <= 0:
                fps = None

            frame_dir = self.frames_root / video_id
            frame_dir.mkdir(parents=True, exist_ok=True)

            extracted_frames: list[VideoFrameMetadata] = []
            frame_index = 0
            while True:
                success, frame = capture.read()
                if not success or frame is None:
                    break

                timestamp_ms = int(capture.get(cv2.CAP_PROP_POS_MSEC))
                frame_name = f"frame_{frame_index:06d}.png"
                frame_path = frame_dir / frame_name
                saved = cv2.imwrite(str(frame_path), frame)
                if not saved:
                    raise ValueError(
                        f"Failed to write extracted frame {frame_index} for video "
                        f"'{video_filename}'."
                    )

                extracted_frames.append(
                    VideoFrameMetadata(
                        frame_index=frame_index,
                        timestamp_ms=timestamp_ms,
                        file_name=frame_name,
                        relative_path=str(Path("sample-data") / "frames" / video_id / frame_name),
                        width=int(frame.shape[1]),
                        height=int(frame.shape[0]),
                    )
                )
                frame_index += 1

            if not extracted_frames:
                raise ValueError(f"No frames could be decoded from video '{video_filename}'.")

            extracted_at = datetime.now(UTC)
            manifest = FrameExtractionResponse(
                video_id=video_id,
                video_filename=video_filename,
                video_path=str(Path(self.settings.upload_dir) / video_filename),
                frame_directory=str(Path("sample-data") / "frames" / video_id),
                manifest_path=str(Path("sample-data") / "frames" / video_id / "manifest.json"),
                fps=fps,
                total_frames=len(extracted_frames),
                extracted_at=extracted_at,
                frames=extracted_frames,
            )
            (frame_dir / "manifest.json").write_text(
                json.dumps(manifest.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            return manifest
        finally:
            capture.release()

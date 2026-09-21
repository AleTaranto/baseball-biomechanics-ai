from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from app.main import app
from app.services.frame_extraction_service import FrameExtractionService
from fastapi.testclient import TestClient


def _create_test_video(video_path: Path, frame_count: int = 4) -> None:
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),  # type: ignore[attr-defined]
        10.0,
        (32, 32),
    )
    assert writer.isOpened()

    try:
        for index in range(frame_count):
            image = np.zeros((32, 32, 3), dtype=np.uint8)
            image[:, :, 0] = (index * 20) % 255
            image[:, :, 1] = (index * 40) % 255
            image[:, :, 2] = (index * 60) % 255
            writer.write(image)
    finally:
        writer.release()


def test_frame_extraction_preserves_order_and_metadata(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    frames_dir = tmp_path / "frames"
    upload_dir.mkdir()

    video_id = "demo-video"
    video_filename = f"{video_id}.avi"
    video_path = upload_dir / video_filename
    _create_test_video(video_path, frame_count=5)
    metadata_path = upload_dir / f"{video_id}.json"
    metadata_path.write_text(
        json.dumps(
            {
                "id": video_id,
                "filename": video_filename,
                "saved_path": str(Path("uploads") / video_filename),
            }
        ),
        encoding="utf-8",
    )

    service = FrameExtractionService()
    service.upload_dir = upload_dir
    service.frames_root = frames_dir

    manifest = service.extract_frames(video_id)

    assert manifest.total_frames == 5
    assert [frame.frame_index for frame in manifest.frames] == list(range(5))
    assert manifest.frames[0].timestamp_ms >= 0
    assert manifest.frames[-1].timestamp_ms >= manifest.frames[0].timestamp_ms
    assert (frames_dir / video_id / "manifest.json").exists()
    assert (frames_dir / video_id / "frame_000000.png").exists()
    assert (frames_dir / video_id / "frame_000004.png").exists()


def test_frame_extraction_rejects_corrupted_video(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    frames_dir = tmp_path / "frames"
    upload_dir.mkdir()

    video_id = "broken-video"
    video_filename = f"{video_id}.avi"
    corrupt_video = upload_dir / video_filename
    corrupt_video.write_bytes(b"not a real video")
    (upload_dir / f"{video_id}.json").write_text(
        json.dumps({
            "id": video_id,
            "filename": video_filename,
            "saved_path": str(Path("uploads") / video_filename),
        }),
        encoding="utf-8",
    )

    service = FrameExtractionService()
    service.upload_dir = upload_dir
    service.frames_root = frames_dir

    with pytest.raises(ValueError, match="could not be opened|No frames could be decoded"):
        service.extract_frames(video_id)


def test_frame_extraction_api_route_returns_manifest() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/videos/non-existent/frames")

    assert response.status_code == 404
    assert "No frame manifest" in response.json()["detail"]

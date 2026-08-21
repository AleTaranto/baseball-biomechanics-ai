from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_video_upload_accepts_valid_mp4() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("example.mp4", b"fake video bytes", "video/mp4")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "example.mp4"
    assert payload["content_type"] == "video/mp4"
    assert payload["size_bytes"] == len(b"fake video bytes")
    assert payload["saved_path"].endswith(".mp4")


def test_video_upload_rejects_invalid_extension() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("example.txt", b"not a video", "text/plain")},
        )

    assert response.status_code == 400
    assert "Unsupported video format" in response.json()["detail"]

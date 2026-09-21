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


def test_stream_video_endpoint_resolves_sample_or_uploaded_video() -> None:
    with TestClient(app) as client:
        upload_resp = client.post(
            "/api/v1/videos/upload",
            files={"file": ("stream_test.mp4", b"mp4 mock bytes content", "video/mp4")},
        )
        assert upload_resp.status_code == 201
        video_id = upload_resp.json()["id"]

        stream_resp = client.get(f"/api/v1/videos/{video_id}/stream")
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"] == "video/mp4"


def test_stream_video_endpoint_not_found_for_missing() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/videos/non_existent_id_12345/stream")
        assert resp.status_code == 404


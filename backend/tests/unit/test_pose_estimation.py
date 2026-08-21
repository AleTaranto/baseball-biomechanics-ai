from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from app.schemas.pose import PoseFrameResult, PoseKeypoint
from app.services.pose_estimation_service import (
    POSE_KEYPOINTS,
    PoseEstimationService,
    PoseEstimator,
)


class MockPoseEstimator(PoseEstimator):
    name = "mock"
    model_name = "mock-model"

    def __init__(self, detected_frames: set[int] | None = None) -> None:
        self.detected_frames = detected_frames or set()

    def estimate(
        self,
        image: np.ndarray,
        *,
        frame_index: int,
        timestamp_ms: int,
    ) -> PoseFrameResult:
        keypoints = {
            key_name: PoseKeypoint(
                name=key_name,
                x=0.1 if frame_index in self.detected_frames else None,
                y=0.2 if frame_index in self.detected_frames else None,
                z=0.0 if frame_index in self.detected_frames else None,
                visibility=0.8 if frame_index in self.detected_frames else 0.0,
                confidence=0.8 if frame_index in self.detected_frames else 0.0,
                detected=frame_index in self.detected_frames,
            )
            for key_name in POSE_KEYPOINTS
        }
        if frame_index in self.detected_frames:
            return PoseFrameResult(
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                detected=True,
                keypoints=keypoints,
            )

        return PoseFrameResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            detected=False,
            error="No person detected in the frame.",
            keypoints=keypoints,
        )


def test_pose_estimator_interface_is_abstract() -> None:
    assert "estimate" in PoseEstimator.__abstractmethods__


def test_pose_estimation_service_persists_keypoints_for_detected_and_missing_frames(
    tmp_path: Path,
) -> None:
    sample_root = tmp_path / "sample-data"
    frame_dir = sample_root / "frames" / "demo-video"
    frame_dir.mkdir(parents=True, exist_ok=True)

    for index in range(2):
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        cv2.imwrite(str(frame_dir / f"frame_{index:06d}.png"), image)

    frame_manifest = {
        "video_filename": "demo-video.mp4",
        "frames": [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "relative_path": "sample-data/frames/demo-video/frame_000000.png",
            },
            {
                "frame_index": 1,
                "timestamp_ms": 33,
                "relative_path": "sample-data/frames/demo-video/frame_000001.png",
            },
        ],
    }
    (frame_dir / "manifest.json").write_text(json.dumps(frame_manifest), encoding="utf-8")

    service = PoseEstimationService(estimator=MockPoseEstimator(detected_frames={0}))
    service.root_dir = tmp_path
    service.frames_root = sample_root / "frames"
    service.pose_root = sample_root / "pose-estimation"

    result = service.estimate_video("demo-video")

    assert result.total_frames == 2
    assert result.processed_frames == 2
    assert result.detected_frames == 1
    assert result.missing_frames == 1
    assert result.frames[0].keypoints["left_shoulder"].x == 0.1
    assert result.frames[1].keypoints["left_shoulder"].x is None
    assert (sample_root / "pose-estimation" / "demo-video" / "manifest.json").exists()


def test_pose_estimation_service_uses_injected_provider(tmp_path: Path) -> None:
    sample_root = tmp_path / "sample-data"
    frame_dir = sample_root / "frames" / "demo-video"
    frame_dir.mkdir(parents=True, exist_ok=True)

    dummy_image = np.zeros((32, 32, 3), dtype=np.uint8)
    cv2.imwrite(str(frame_dir / "frame_000000.png"), dummy_image)
    (frame_dir / "manifest.json").write_text(
        json.dumps(
            {
                "video_filename": "demo-video.mp4",
                "frames": [
                    {
                        "frame_index": 0,
                        "timestamp_ms": 0,
                        "relative_path": "sample-data/frames/demo-video/frame_000000.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    mock_estimator = MockPoseEstimator(detected_frames={0})
    service = PoseEstimationService(estimator=mock_estimator)
    service.root_dir = tmp_path
    service.frames_root = sample_root / "frames"
    service.pose_root = sample_root / "pose-estimation"

    result = service.estimate_video("demo-video")

    assert result.provider == "mock"
    assert result.model_name == "mock-model"
    assert result.frames[0].detected is True

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.request import urlretrieve

import cv2
import mediapipe as mp  # type: ignore[import-untyped]
import numpy as np
from app.core.config import get_settings
from app.schemas.pose import PoseEstimationResponse, PoseFrameResult, PoseKeypoint
from mediapipe.tasks.python import BaseOptions  # type: ignore[import-untyped]
from mediapipe.tasks.python.vision import (  # type: ignore[import-untyped]
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)

POSE_KEYPOINTS = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


class PoseEstimator(ABC):
    name: str = "base-estimator"
    model_name: str = "base-model"

    @abstractmethod
    def estimate(
        self,
        image: np.ndarray,
        *,
        frame_index: int,
        timestamp_ms: int,
    ) -> PoseFrameResult:
        """Estimate pose coordinates for a given image frame."""

    def save_debug_overlay(
        self,
        *,
        image: np.ndarray,
        frame_path: Path,
        output_dir: Path,
    ) -> Path | None:
        del image, frame_path, output_dir
        return None


class MediaPipePoseEstimator(PoseEstimator):
    name = "mediapipe"
    model_name = "pose_landmarker_lite.task"
    _MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
    )

    def __init__(
        self,
        *,
        model_path: str | Path | None = None,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.model_path = self._resolve_model_path(model_path)
        self._pose = PoseLandmarker.create_from_options(
            PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=RunningMode.IMAGE,
                min_pose_detection_confidence=min_detection_confidence,
                min_pose_presence_confidence=min_tracking_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        )

    def _resolve_model_path(self, model_path: str | Path | None) -> Path:
        if model_path is not None:
            path = Path(model_path)
            if path.exists():
                return path
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            self._download_model(path)
            return path

        default_dir = Path(__file__).resolve().parents[3] / "sample-data" / "models"
        default_dir.mkdir(parents=True, exist_ok=True)
        candidate = default_dir / "pose_landmarker_lite.task"
        if not candidate.exists():
            self._download_model(candidate)
        return candidate

    def _download_model(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(self._MODEL_URL, str(destination))

    def _empty_keypoints(self) -> dict[str, PoseKeypoint]:
        return {
            key_name: PoseKeypoint(
                name=key_name,
                x=None,
                y=None,
                z=None,
                visibility=0.0,
                confidence=0.0,
                detected=False,
            )
            for key_name in POSE_KEYPOINTS
        }

    def _build_keypoint(self, key_name: str, landmark: object) -> PoseKeypoint:
        landmark_obj = cast(Any, landmark)
        visibility = getattr(landmark_obj, "visibility", None)
        confidence = (
            visibility if visibility is not None else getattr(landmark_obj, "confidence", None)
        )
        return PoseKeypoint(
            name=key_name,
            x=float(landmark_obj.x) if getattr(landmark_obj, "x", None) is not None else None,
            y=float(landmark_obj.y) if getattr(landmark_obj, "y", None) is not None else None,
            z=float(landmark_obj.z) if getattr(landmark_obj, "z", None) is not None else None,
            visibility=float(visibility) if visibility is not None else None,
            confidence=float(confidence) if confidence is not None else None,
            detected=True,
        )

    def estimate(
        self,
        image: np.ndarray,
        *,
        frame_index: int,
        timestamp_ms: int,
    ) -> PoseFrameResult:
        if image is None or image.size == 0:
            return PoseFrameResult(
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                detected=False,
                error="Input frame is empty.",
                keypoints=self._empty_keypoints(),
            )

        rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._pose.detect(mp_image)
        if not result.pose_landmarks:
            return PoseFrameResult(
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                detected=False,
                error="No person detected in the frame.",
                keypoints=self._empty_keypoints(),
            )

        landmarks = result.pose_landmarks[0]
        keypoints: dict[str, PoseKeypoint] = {}
        for key_name, index in POSE_KEYPOINTS.items():
            if index < len(landmarks):
                keypoints[key_name] = self._build_keypoint(key_name, landmarks[index])
            else:
                keypoints[key_name] = PoseKeypoint(
                    name=key_name,
                    x=None,
                    y=None,
                    z=None,
                    visibility=0.0,
                    confidence=0.0,
                    detected=False,
                )

        return PoseFrameResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            detected=True,
            keypoints=keypoints,
        )

    def save_debug_overlay(
        self,
        *,
        image: np.ndarray,
        frame_path: Path,
        output_dir: Path,
    ) -> Path | None:
        rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._pose.detect(mp_image)
        if not result.pose_landmarks:
            return None

        output_dir.mkdir(parents=True, exist_ok=True)
        debug_frame = image.copy()
        height, width, _ = debug_frame.shape
        connections = [
            (11, 13),
            (13, 15),
            (12, 14),
            (14, 16),
            (11, 12),
            (23, 11),
            (24, 12),
            (23, 24),
            (23, 25),
            (25, 27),
            (24, 26),
            (26, 28),
        ]
        for pose_landmarks in result.pose_landmarks:
            for start_index, end_index in connections:
                start = pose_landmarks[start_index]
                end = pose_landmarks[end_index]
                if start.visibility is None or end.visibility is None:
                    continue
                if start.visibility < 0.2 or end.visibility < 0.2:
                    continue
                start_pt = (int(start.x * width), int(start.y * height))
                end_pt = (int(end.x * width), int(end.y * height))
                cv2.line(debug_frame, start_pt, end_pt, (0, 255, 0), 2)
            for index, landmark in enumerate(pose_landmarks):
                if index not in POSE_KEYPOINTS.values():
                    continue
                if landmark.visibility is None or landmark.visibility < 0.2:
                    continue
                pt = (int(landmark.x * width), int(landmark.y * height))
                cv2.circle(debug_frame, pt, 4, (0, 0, 255), -1)
        debug_path = output_dir / frame_path.name.replace(".png", "_debug.png")
        cv2.imwrite(str(debug_path), debug_frame)
        return debug_path


class PoseEstimationService:
    def __init__(self, estimator: PoseEstimator | None = None) -> None:
        self.settings = get_settings()
        self.root_dir = Path(__file__).resolve().parents[3]
        self.frames_root = self.root_dir / "sample-data" / "frames"
        self.pose_root = self.root_dir / "sample-data" / "pose-estimation"
        self.estimator = estimator or MediaPipePoseEstimator()

    def _frame_manifest_path(self, video_id: str) -> Path:
        return self.frames_root / video_id / "manifest.json"

    def _pose_manifest_path(self, video_id: str) -> Path:
        return self.pose_root / video_id / "manifest.json"

    def load_manifest(self, video_id: str) -> PoseEstimationResponse:
        manifest_path = self._pose_manifest_path(video_id)
        if not manifest_path.exists():
            raise ValueError(f"No pose manifest exists for video id '{video_id}'.")

        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return PoseEstimationResponse.model_validate(payload)

    def estimate_video(self, video_id: str) -> PoseEstimationResponse:
        frame_manifest_path = self._frame_manifest_path(video_id)
        if not frame_manifest_path.exists():
            raise ValueError(f"No frame manifest exists for video id '{video_id}'.")

        frame_manifest = json.loads(frame_manifest_path.read_text(encoding="utf-8"))
        frame_entries = frame_manifest.get("frames", [])
        if not frame_entries:
            raise ValueError(f"The frame set for video id '{video_id}' is empty.")

        output_dir = self.pose_root / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        debug_dir = output_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

        processed_frames: list[PoseFrameResult] = []
        for frame_entry in frame_entries:
            frame_index = int(frame_entry["frame_index"])
            timestamp_ms = int(frame_entry["timestamp_ms"])
            relative_path = str(frame_entry["relative_path"]).replace("\\", "/")
            frame_path = self.root_dir / relative_path
            if not frame_path.exists():
                processed_frames.append(
                    PoseFrameResult(
                        frame_index=frame_index,
                        timestamp_ms=timestamp_ms,
                        detected=False,
                        error=f"Missing frame file '{relative_path}'.",
                        keypoints={
                            key_name: PoseKeypoint(
                                name=key_name,
                                x=None,
                                y=None,
                                z=None,
                                visibility=0.0,
                                confidence=0.0,
                                detected=False,
                            )
                            for key_name in POSE_KEYPOINTS
                        },
                    )
                )
                continue

            image = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
            if image is None:
                processed_frames.append(
                    PoseFrameResult(
                        frame_index=frame_index,
                        timestamp_ms=timestamp_ms,
                        detected=False,
                        error=f"Frame '{frame_path.name}' could not be decoded.",
                        keypoints={
                            key_name: PoseKeypoint(
                                name=key_name,
                                x=None,
                                y=None,
                                z=None,
                                visibility=0.0,
                                confidence=0.0,
                                detected=False,
                            )
                            for key_name in POSE_KEYPOINTS
                        },
                    )
                )
                continue

            result = self.estimator.estimate(
                image,
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
            )
            processed_frames.append(result)

            if isinstance(self.estimator, MediaPipePoseEstimator):
                self.estimator.save_debug_overlay(
                    image=image,
                    frame_path=frame_path,
                    output_dir=debug_dir,
                )

        detected_frames = sum(1 for item in processed_frames if item.detected)
        missing_frames = sum(1 for item in processed_frames if not item.detected)
        generated_at = datetime.now(UTC)
        response = PoseEstimationResponse(
            video_id=video_id,
            video_filename=frame_manifest.get("video_filename", "unknown"),
            provider=self.estimator.name,
            model_name=self.estimator.model_name,
            frame_directory=str(Path("sample-data") / "frames" / video_id),
            manifest_path=str(Path("sample-data") / "pose-estimation" / video_id / "manifest.json"),
            total_frames=len(frame_entries),
            processed_frames=len(processed_frames),
            detected_frames=detected_frames,
            missing_frames=missing_frames,
            generated_at=generated_at,
            frames=processed_frames,
        )
        manifest_path = self._pose_manifest_path(video_id)
        manifest_path.write_text(
            json.dumps(response.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return response

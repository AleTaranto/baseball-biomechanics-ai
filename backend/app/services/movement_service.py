from __future__ import annotations

import math
from collections.abc import Iterable

from app.schemas.movement import (
    DEFAULT_JOINTS,
    FramePose,
    JointObservation,
    MovementRecording,
    PoseSequenceIssue,
    PoseSequenceQuality,
    PoseSequenceValidationResult,
)
from app.schemas.pose import PoseEstimationResponse


class MovementDataMapper:
    """Adapter from raw provider output to the canonical movement model.

    The raw provider payload is treated as a technical artifact for debugging and
    provenance; this mapper produces the canonical representation used by the
    motion-analysis pipeline.
    """

    @staticmethod
    def _joint_from_keypoint(
        key_name: str,
        keypoint: object,
    ) -> JointObservation:
        x = getattr(keypoint, "x", None)
        y = getattr(keypoint, "y", None)
        z = getattr(keypoint, "z", None)
        confidence = getattr(keypoint, "confidence", None)
        visibility = getattr(keypoint, "visibility", None)
        detected = bool(getattr(keypoint, "detected", True))

        return JointObservation(
            joint_name=key_name,
            x=float(x) if x is not None else None,
            y=float(y) if y is not None else None,
            z=float(z) if z is not None else None,
            confidence=float(confidence) if confidence is not None else None,
            visibility=float(visibility) if visibility is not None else None,
            detected=detected,
        )

    @classmethod
    def from_pose_estimation_response(
        cls,
        response: PoseEstimationResponse,
        *,
        recording_id: str | None = None,
        fps: float | None = None,
    ) -> MovementRecording:
        frames: list[FramePose] = []
        for frame_result in response.frames:
            joints: dict[str, JointObservation] = {}
            for joint_name, keypoint in frame_result.keypoints.items():
                if joint_name not in DEFAULT_JOINTS:
                    continue
                joints[joint_name] = cls._joint_from_keypoint(joint_name, keypoint)
            frames.append(
                FramePose(
                    frame_index=frame_result.frame_index,
                    timestamp=frame_result.timestamp_ms,
                    detected=frame_result.detected,
                    joints=joints,
                )
            )

        duration = max((frame.timestamp for frame in frames), default=0)
        quality_summary = PoseSequenceQuality(
            total_frames=len(frames),
            frames_with_pose=sum(1 for frame in frames if frame.detected),
            frames_without_pose=sum(1 for frame in frames if not frame.detected),
            missing_joint_counts=0,
            low_confidence_joint_counts=0,
            temporal_continuity_status="pending",
        )
        return MovementRecording(
            recording_id=recording_id or f"{response.video_id}-movement",
            source_video_id=response.video_id,
            fps=fps,
            duration=duration,
            frames=frames,
            quality_summary=quality_summary,
        )


class PoseSequenceValidator:
    def __init__(
        self,
        *,
        low_confidence_threshold: float = 0.3,
        max_temporal_gap_ms: int = 200,
    ) -> None:
        self.low_confidence_threshold = float(low_confidence_threshold)
        self.max_temporal_gap_ms = int(max_temporal_gap_ms)

    def _is_coordinate_valid(self, value: float | None) -> bool:
        if value is None:
            return False
        return math.isfinite(value) and 0.0 <= value <= 1.0

    def _build_status(
        self,
        issues: Iterable[PoseSequenceIssue],
        quality_summary: PoseSequenceQuality,
    ) -> str:
        has_order_or_gap = any(
            issue.code in {"missing-frame", "timestamp-order", "temporal-gap"}
            for issue in issues
        )
        if quality_summary.frames_without_pose > 0 or has_order_or_gap:
            return "warning"
        if quality_summary.low_confidence_joint_counts > 0:
            return "warning"
        if quality_summary.missing_joint_counts > 0:
            return "warning"
        return "continuous"

    def validate(self, recording: MovementRecording) -> PoseSequenceValidationResult:
        issues: list[PoseSequenceIssue] = []
        missing_joint_counts = 0
        low_confidence_joint_counts = 0

        sorted_frames = sorted(recording.frames, key=lambda frame: frame.frame_index)
        frame_indices = [frame.frame_index for frame in sorted_frames]
        if frame_indices:
            expected_range = set(range(frame_indices[0], frame_indices[-1] + 1))
            observed = set(frame_indices)
            missing_frames = sorted(expected_range - observed)
            for frame_index in missing_frames:
                issues.append(
                    PoseSequenceIssue(
                        code="missing-frame",
                        message=f"Frame index {frame_index} is missing from the recording.",
                        frame_index=frame_index,
                    )
                )

        previous_index: int | None = None
        previous_timestamp: int | None = None
        for frame in sorted_frames:
            if previous_index is not None and frame.frame_index <= previous_index:
                issues.append(
                    PoseSequenceIssue(
                        code="frame-order",
                        message=(
                            f"Frame index {frame.frame_index} is not strictly increasing after "
                            f"{previous_index}."
                        ),
                        frame_index=frame.frame_index,
                    )
                )
            if previous_timestamp is not None and frame.timestamp < previous_timestamp:
                issues.append(
                    PoseSequenceIssue(
                        code="timestamp-order",
                        message=(
                            f"Timestamp {frame.timestamp} is out of order after "
                            f"{previous_timestamp}."
                        ),
                        frame_index=frame.frame_index,
                    )
                )
            if previous_timestamp is not None:
                delta = frame.timestamp - previous_timestamp
                if delta > self.max_temporal_gap_ms:
                    issues.append(
                        PoseSequenceIssue(
                            code="temporal-gap",
                            message=(
                                f"Temporal discontinuity detected between consecutive frames: "
                                f"{delta} ms exceeds threshold {self.max_temporal_gap_ms} ms."
                            ),
                            frame_index=frame.frame_index,
                        )
                    )

            if not frame.detected:
                issues.append(
                    PoseSequenceIssue(
                        code="frame-without-pose",
                        message=f"Frame {frame.frame_index} has no detected pose.",
                        frame_index=frame.frame_index,
                    )
                )

            missing_joints = [
                name
                for name in DEFAULT_JOINTS
                if name not in frame.joints
                or not frame.joints[name].detected
                or frame.joints[name].x is None
                or frame.joints[name].y is None
            ]
            if missing_joints:
                missing_joint_counts += len(missing_joints)
                for joint_name in missing_joints:
                    issues.append(
                        PoseSequenceIssue(
                            code="missing-joint",
                            message=(
                                f"Joint {joint_name} is missing or invalid in frame "
                                f"{frame.frame_index}."
                            ),
                            frame_index=frame.frame_index,
                            joint_name=joint_name,
                        )
                    )

            for joint_name, joint in frame.joints.items():
                if not self._is_coordinate_valid(joint.x) or not self._is_coordinate_valid(joint.y):
                    issues.append(
                        PoseSequenceIssue(
                            code="invalid-coordinate",
                            message=(
                                f"Joint {joint_name} has an invalid coordinate in frame "
                                f"{frame.frame_index}."
                            ),
                            frame_index=frame.frame_index,
                            joint_name=joint_name,
                        )
                    )
                if (
                    joint.confidence is not None
                    and joint.confidence < self.low_confidence_threshold
                ):
                    low_confidence_joint_counts += 1
                    issues.append(
                        PoseSequenceIssue(
                            code="low-confidence",
                            message=(
                                f"Joint {joint_name} has confidence {joint.confidence:.3f}, "
                                f"below threshold {self.low_confidence_threshold:.3f}."
                            ),
                            frame_index=frame.frame_index,
                            joint_name=joint_name,
                        )
                    )
                if (
                    joint.visibility is not None
                    and joint.visibility < self.low_confidence_threshold
                ):
                    low_confidence_joint_counts += 1
                    issues.append(
                        PoseSequenceIssue(
                            code="low-visibility",
                            message=(
                                f"Joint {joint_name} has visibility {joint.visibility:.3f}, "
                                f"below threshold {self.low_confidence_threshold:.3f}."
                            ),
                            frame_index=frame.frame_index,
                            joint_name=joint_name,
                        )
                    )

            previous_index = frame.frame_index
            previous_timestamp = frame.timestamp

        quality_summary = PoseSequenceQuality(
            total_frames=len(sorted_frames),
            frames_with_pose=sum(1 for frame in sorted_frames if frame.detected),
            frames_without_pose=sum(1 for frame in sorted_frames if not frame.detected),
            missing_joint_counts=missing_joint_counts,
            low_confidence_joint_counts=low_confidence_joint_counts,
            temporal_continuity_status="pending",
        )
        quality_summary.temporal_continuity_status = self._build_status(issues, quality_summary)

        return PoseSequenceValidationResult(quality_summary=quality_summary, issues=issues)


class MovementDataService:
    def __init__(
        self,
        *,
        low_confidence_threshold: float = 0.3,
        max_temporal_gap_ms: int = 200,
    ) -> None:
        self.validator = PoseSequenceValidator(
            low_confidence_threshold=low_confidence_threshold,
            max_temporal_gap_ms=max_temporal_gap_ms,
        )

    def build_recording(
        self,
        response: PoseEstimationResponse,
        *,
        recording_id: str | None = None,
        fps: float | None = None,
    ) -> MovementRecording:
        recording = MovementDataMapper.from_pose_estimation_response(
            response,
            recording_id=recording_id,
            fps=fps,
        )
        validation = self.validator.validate(recording)
        recording.quality_summary = validation.quality_summary
        return recording

    def validate_recording(self, recording: MovementRecording) -> PoseSequenceValidationResult:
        return self.validator.validate(recording)

from __future__ import annotations

import json
import math
from pathlib import Path

from app.schemas.kinematics import (
    AngleMetric,
    KinematicFrame,
    KinematicRecording,
    SegmentVectorMetric,
    VelocityMetric,
)
from app.schemas.movement import FramePose, JointObservation, MovementRecording

ANGLE_DEFINITIONS: dict[str, tuple[str, str, str]] = {
    "left_elbow_angle": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow_angle": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_knee_angle": ("left_hip", "left_knee", "left_ankle"),
    "right_knee_angle": ("right_hip", "right_knee", "right_ankle"),
}

SEGMENT_DEFINITIONS: dict[str, tuple[str, str]] = {
    "left_upper_arm": ("left_shoulder", "left_elbow"),
    "right_upper_arm": ("right_shoulder", "right_elbow"),
    "left_forearm": ("left_elbow", "left_wrist"),
    "right_forearm": ("right_elbow", "right_wrist"),
    "left_thigh": ("left_hip", "left_knee"),
    "right_thigh": ("right_hip", "right_knee"),
    "left_shank": ("left_knee", "left_ankle"),
    "right_shank": ("right_knee", "right_ankle"),
    "shoulder_line": ("left_shoulder", "right_shoulder"),
    "hip_line": ("left_hip", "right_hip"),
}

VELOCITY_JOINTS = [
    "left_wrist",
    "right_wrist",
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
]


class KinematicAnalysisService:
    def __init__(self, *, low_confidence_threshold: float = 0.3) -> None:
        self.low_confidence_threshold = float(low_confidence_threshold)

    @staticmethod
    def _coord_from_joint(joint: JointObservation | None) -> tuple[float, float] | None:
        if joint is None or not joint.detected:
            return None
        if joint.x is None or joint.y is None:
            return None
        if not math.isfinite(joint.x) or not math.isfinite(joint.y):
            return None
        if not (0.0 <= joint.x <= 1.0 and 0.0 <= joint.y <= 1.0):
            return None
        return float(joint.x), float(joint.y)

    @staticmethod
    def _joint_quality(joint: JointObservation | None) -> float | None:
        if joint is None:
            return None
        values: list[float] = []
        if joint.confidence is not None:
            values.append(float(joint.confidence))
        if joint.visibility is not None:
            values.append(float(joint.visibility))
        if not values:
            return None
        return sum(values) / len(values)

    @classmethod
    def _input_quality_for_joints(
        cls,
        *joints: JointObservation | None,
    ) -> float | None:
        qualities = [
            quality
            for quality in (cls._joint_quality(joint) for joint in joints)
            if quality is not None
        ]
        if not qualities:
            return None
        return sum(qualities) / len(qualities)

    @classmethod
    def _compute_angle_metric(
        cls,
        frame: FramePose,
        *,
        joint_a: str,
        joint_b: str,
        joint_c: str,
        low_confidence_threshold: float,
    ) -> AngleMetric:
        jointA = frame.joints.get(joint_a)
        jointB = frame.joints.get(joint_b)
        jointC = frame.joints.get(joint_c)
        if jointA is None or jointB is None or jointC is None:
            return AngleMetric(valid=False, reason="missing_joint", input_quality=None)

        coord_a = cls._coord_from_joint(jointA)
        coord_b = cls._coord_from_joint(jointB)
        coord_c = cls._coord_from_joint(jointC)
        if coord_a is None or coord_b is None or coord_c is None:
            return AngleMetric(valid=False, reason="invalid_coordinate", input_quality=None)

        input_quality = cls._input_quality_for_joints(jointA, jointB, jointC)
        if input_quality is not None and input_quality < low_confidence_threshold:
            return AngleMetric(
                value_degrees=None,
                valid=False,
                reason="low_confidence_input",
                input_quality=input_quality,
            )

        vec_a = (coord_a[0] - coord_b[0], coord_a[1] - coord_b[1])
        vec_c = (coord_c[0] - coord_b[0], coord_c[1] - coord_b[1])
        dot = vec_a[0] * vec_c[0] + vec_a[1] * vec_c[1]
        norm_a = math.hypot(*vec_a)
        norm_c = math.hypot(*vec_c)
        if norm_a == 0.0 or norm_c == 0.0:
            return AngleMetric(
                value_degrees=None,
                valid=False,
                reason="zero_length_segment",
                input_quality=input_quality,
            )

        cosine = max(-1.0, min(1.0, dot / (norm_a * norm_c)))
        angle_deg = math.degrees(math.acos(cosine))
        return AngleMetric(
            value_degrees=angle_deg,
            valid=True,
            reason=None,
            input_quality=input_quality,
        )

    @staticmethod
    def _segment_vector_metric(
        frame: FramePose,
        *,
        start_joint: str,
        end_joint: str,
    ) -> SegmentVectorMetric:
        start = frame.joints.get(start_joint)
        end = frame.joints.get(end_joint)
        if start is None or end is None:
            return SegmentVectorMetric(valid=False, reason="missing_joint")

        start_coord = KinematicAnalysisService._coord_from_joint(start)
        end_coord = KinematicAnalysisService._coord_from_joint(end)
        if start_coord is None or end_coord is None:
            return SegmentVectorMetric(valid=False, reason="invalid_coordinate")

        vector = (end_coord[0] - start_coord[0], end_coord[1] - start_coord[1])
        magnitude = math.hypot(*vector)
        if magnitude == 0.0:
            return SegmentVectorMetric(
                vector={"x": vector[0], "y": vector[1]},
                magnitude=0.0,
                normalized_vector={"x": 0.0, "y": 0.0},
                valid=False,
                reason="zero_length_segment",
            )

        normalized = (vector[0] / magnitude, vector[1] / magnitude)
        input_quality = KinematicAnalysisService._input_quality_for_joints(start, end)
        return SegmentVectorMetric(
            vector={"x": vector[0], "y": vector[1]},
            magnitude=magnitude,
            normalized_vector={"x": normalized[0], "y": normalized[1]},
            valid=True,
            reason=None,
            input_quality=input_quality,
        )

    @classmethod
    def _compute_velocity_metric(
        cls,
        current_frame: FramePose,
        previous_frame: FramePose | None,
        *,
        joint_name: str,
        low_confidence_threshold: float,
    ) -> VelocityMetric:
        if previous_frame is None:
            return VelocityMetric(valid=False, reason="no_previous_frame")

        current_joint = current_frame.joints.get(joint_name)
        previous_joint = previous_frame.joints.get(joint_name)
        if current_joint is None or previous_joint is None:
            return VelocityMetric(valid=False, reason="missing_joint")

        current_coord = cls._coord_from_joint(current_joint)
        previous_coord = cls._coord_from_joint(previous_joint)
        if current_coord is None or previous_coord is None:
            return VelocityMetric(valid=False, reason="invalid_coordinate")

        dt_seconds = current_frame.timestamp_seconds - previous_frame.timestamp_seconds
        if dt_seconds <= 0.0:
            return VelocityMetric(valid=False, reason="zero_or_negative_time_delta")

        input_quality = cls._input_quality_for_joints(current_joint, previous_joint)
        if input_quality is not None and input_quality < low_confidence_threshold:
            return VelocityMetric(
                value_normalized_units_per_second=None,
                valid=False,
                reason="low_confidence_input",
                input_quality=input_quality,
            )

        distance = math.hypot(
            current_coord[0] - previous_coord[0],
            current_coord[1] - previous_coord[1],
        )
        value = distance / dt_seconds if dt_seconds > 0.0 else None
        return VelocityMetric(
            value_normalized_units_per_second=value,
            valid=value is not None,
            reason=None if value is not None else "invalid_velocity",
            input_quality=input_quality,
        )

    @classmethod
    def _analyze_frame(
        cls,
        frame: FramePose,
        *,
        previous_frame: FramePose | None,
        low_confidence_threshold: float,
    ) -> KinematicFrame:
        joint_angles: dict[str, AngleMetric] = {}
        for name, (a, b, c) in ANGLE_DEFINITIONS.items():
            joint_angles[name] = cls._compute_angle_metric(
                frame,
                joint_a=a,
                joint_b=b,
                joint_c=c,
                low_confidence_threshold=low_confidence_threshold,
            )

        segment_vectors: dict[str, SegmentVectorMetric] = {}
        for name, (start_joint, end_joint) in SEGMENT_DEFINITIONS.items():
            segment_vectors[name] = cls._segment_vector_metric(
                frame,
                start_joint=start_joint,
                end_joint=end_joint,
            )

        linear_velocities: dict[str, VelocityMetric] = {}
        for joint_name in VELOCITY_JOINTS:
            linear_velocities[joint_name] = cls._compute_velocity_metric(
                frame,
                previous_frame,
                joint_name=joint_name,
                low_confidence_threshold=low_confidence_threshold,
            )

        return KinematicFrame(
            frame_index=frame.frame_index,
            timestamp_seconds=frame.timestamp_seconds,
            joint_angles=joint_angles,
            segment_vectors=segment_vectors,
            linear_velocities=linear_velocities,
        )

    def build_recording(self, movement: MovementRecording) -> KinematicRecording:
        frames: list[KinematicFrame] = []
        previous_frame: FramePose | None = None
        for frame in sorted(movement.frames, key=lambda item: item.frame_index):
            frames.append(
                self._analyze_frame(
                    frame,
                    previous_frame=previous_frame,
                    low_confidence_threshold=self.low_confidence_threshold,
                )
            )
            previous_frame = frame

        return KinematicRecording(
            recording_id=f"{movement.recording_id}-kinematics",
            source_video_id=movement.source_video_id,
            source_recording_id=movement.recording_id,
            fps=movement.fps,
            duration_seconds=movement.duration_seconds,
            frames=frames,
        )

    @staticmethod
    def load_recording(
        video_id: str,
        *,
        output_dir: str | Path | None = None,
    ) -> KinematicRecording:
        base_dir = (
            Path(output_dir)
            if output_dir is not None
            else Path(__file__).resolve().parents[3] / "sample-data" / "kinematics"
        )
        target = base_dir / f"{video_id}.json"
        if not target.exists():
            raise ValueError(f"No kinematic recording exists for video id '{video_id}'.")
        payload = json.loads(target.read_text(encoding="utf-8"))
        return KinematicRecording.model_validate(payload)

    @staticmethod
    def persist_recording(recording: KinematicRecording, output_dir: str | Path) -> Path:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        target = path / f"{recording.source_video_id}.json"
        target.write_text(json.dumps(recording.model_dump(mode="json"), indent=2), encoding="utf-8")
        return target

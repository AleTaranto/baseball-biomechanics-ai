from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

from app.schemas.movement import FramePose, JointObservation, MovementRecording
from app.schemas.pose_quality import (
    ArmLegComparison,
    JointQualitySummary,
    PoseQualityReport,
    PotentialTrackingAnomaly,
    TemporalQualitySummary,
    WorstFrameInspection,
)

DEFAULT_JOINTS = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]
ARM_JOINTS = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
]
LEG_JOINTS = [
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


class PoseQualityAnalysisService:
    def __init__(
        self,
        *,
        low_confidence_threshold: float = 0.3,
        acceptable_confidence_threshold: float = 0.5,
        high_confidence_threshold: float = 0.8,
        large_displacement_threshold: float = 0.15,
        direction_change_threshold_degrees: float = 120.0,
        confidence_drop_threshold: float = 0.3,
    ) -> None:
        self.low_confidence_threshold = float(low_confidence_threshold)
        self.acceptable_confidence_threshold = float(acceptable_confidence_threshold)
        self.high_confidence_threshold = float(high_confidence_threshold)
        self.large_displacement_threshold = float(large_displacement_threshold)
        self.direction_change_threshold_degrees = float(direction_change_threshold_degrees)
        self.confidence_drop_threshold = float(confidence_drop_threshold)

    @staticmethod
    def _statistics(
        values: list[float],
    ) -> tuple[float | None, float | None, float | None, float | None]:
        if not values:
            return None, None, None, None
        return (
            sum(values) / len(values),
            float(median(values)),
            min(values),
            max(values),
        )

    @staticmethod
    def _classify_confidence(value: float | None) -> str:
        if value is None:
            return "unknown"
        if value >= 0.8:
            return "high_confidence"
        if value >= 0.5:
            return "acceptable_confidence"
        return "low_confidence"

    @staticmethod
    def _detected_joint(frame: FramePose, joint_name: str) -> JointObservation | None:
        joint = frame.joints.get(joint_name)
        if joint is None or not joint.detected:
            return None
        return joint

    @staticmethod
    def _safe_point(joint: JointObservation | None) -> tuple[float, float] | None:
        if joint is None or not joint.detected:
            return None
        if joint.x is None or joint.y is None:
            return None
        if not math.isfinite(float(joint.x)) or not math.isfinite(float(joint.y)):
            return None
        return float(joint.x), float(joint.y)

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @classmethod
    def _direction_angle(
        cls,
        vector_a: tuple[float, float],
        vector_b: tuple[float, float],
    ) -> float:
        if vector_a == (0.0, 0.0) or vector_b == (0.0, 0.0):
            return 0.0
        dot = vector_a[0] * vector_b[0] + vector_a[1] * vector_b[1]
        norm_product = math.hypot(*vector_a) * math.hypot(*vector_b)
        if norm_product == 0.0:
            return 0.0
        cosine = max(-1.0, min(1.0, dot / norm_product))
        return math.degrees(math.acos(cosine))

    def _analyze_joint_quality(
        self,
        recording: MovementRecording,
        joint_name: str,
    ) -> JointQualitySummary:
        total_frames = len(recording.frames)
        detected_frames = 0
        confidence_values: list[float] = []
        visibility_values: list[float] = []
        low_confidence_frames = 0
        for frame in recording.frames:
            joint = self._detected_joint(frame, joint_name)
            if joint is None:
                continue
            detected_frames += 1
            if joint.confidence is not None:
                confidence_values.append(float(joint.confidence))
                if joint.confidence < self.low_confidence_threshold:
                    low_confidence_frames += 1
            if joint.visibility is not None:
                visibility_values.append(float(joint.visibility))

        detection_rate = (detected_frames / total_frames) if total_frames else 0.0
        mean_confidence, median_confidence, min_confidence, max_confidence = self._statistics(
            confidence_values
        )
        mean_visibility, median_visibility, min_visibility, _ = self._statistics(visibility_values)
        low_confidence_percentage = (
            (low_confidence_frames / total_frames * 100.0) if total_frames else 0.0
        )
        confidence_band = self._classify_confidence(mean_confidence)
        if mean_confidence is None:
            confidence_band = "unknown"

        return JointQualitySummary(
            joint_name=joint_name,
            total_frames=total_frames,
            detected_frames=detected_frames,
            detection_rate=detection_rate,
            missing_frames=total_frames - detected_frames,
            mean_confidence=mean_confidence,
            median_confidence=median_confidence,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            mean_visibility=mean_visibility,
            median_visibility=median_visibility,
            min_visibility=min_visibility,
            low_confidence_frames=low_confidence_frames,
            low_confidence_percentage=low_confidence_percentage,
            confidence_band=confidence_band,
        )

    def _analyze_temporal_quality(
        self,
        recording: MovementRecording,
        joint_name: str,
    ) -> TemporalQualitySummary:
        low_confidence_indices: list[int] = []
        missing_indices: list[int] = []
        periods: list[list[int]] = []
        current_period: list[int] = []

        for frame_index, frame in enumerate(recording.frames):
            joint = self._detected_joint(frame, joint_name)
            if joint is None:
                missing_indices.append(frame_index)
                if current_period:
                    periods.append(current_period)
                    current_period = []
                continue
            confidence = joint.confidence
            is_low = confidence is not None and confidence < self.low_confidence_threshold
            if is_low:
                low_confidence_indices.append(frame_index)
                current_period.append(frame_index)
            elif current_period:
                periods.append(current_period)
                current_period = []

        if current_period:
            periods.append(current_period)

        longest_period = max((len(period) for period in periods), default=0)
        affected_percentage = (
            (len(set(low_confidence_indices + missing_indices)) / len(recording.frames) * 100.0)
            if recording.frames
            else 0.0
        )

        return TemporalQualitySummary(
            joint_name=joint_name,
            low_confidence_frame_indices=low_confidence_indices,
            missing_detection_frame_indices=missing_indices,
            low_confidence_periods=periods,
            longest_low_confidence_period=longest_period,
            affected_percentage=affected_percentage,
        )

    def _detect_anomalies(self, recording: MovementRecording) -> list[PotentialTrackingAnomaly]:
        anomalies: list[PotentialTrackingAnomaly] = []
        for joint_name in DEFAULT_JOINTS:
            previous: FramePose | None = None
            previous_previous: FramePose | None = None
            for frame_index, frame in enumerate(recording.frames):
                joint = self._detected_joint(frame, joint_name)
                prev_joint = (
                    self._detected_joint(previous, joint_name)
                    if previous is not None
                    else None
                )
                prev_prev_joint = (
                    self._detected_joint(previous_previous, joint_name)
                    if previous_previous is not None
                    else None
                )

                if joint is not None and prev_joint is not None:
                    current_point = self._safe_point(joint)
                    previous_point = self._safe_point(prev_joint)
                    if current_point is not None and previous_point is not None:
                        displacement = self._distance(current_point, previous_point)
                        if displacement > self.large_displacement_threshold:
                            anomalies.append(
                                PotentialTrackingAnomaly(
                                    joint_name=joint_name,
                                    frame_index=frame_index,
                                    timestamp_seconds=frame.timestamp_seconds,
                                    anomaly_type="large_displacement",
                                    severity=displacement,
                                    details=(
                                        f"Joint moved {displacement:.3f} normalized units "
                                        f"between consecutive frames."
                                    ),
                                )
                            )

                        if prev_prev_joint is not None:
                            prev_point = self._safe_point(prev_joint)
                            prev_prev_point = self._safe_point(prev_prev_joint)
                            if prev_point is not None and prev_prev_point is not None:
                                vector_a = (
                                    prev_point[0] - prev_prev_point[0],
                                    prev_point[1] - prev_prev_point[1],
                                )
                                vector_b = (
                                    current_point[0] - prev_point[0],
                                    current_point[1] - prev_point[1],
                                )
                                angle = self._direction_angle(vector_a, vector_b)
                                if angle > self.direction_change_threshold_degrees:
                                    anomalies.append(
                                        PotentialTrackingAnomaly(
                                            joint_name=joint_name,
                                            frame_index=frame_index,
                                            timestamp_seconds=frame.timestamp_seconds,
                                            anomaly_type="direction_change",
                                            severity=angle,
                                            details=(
                                                f"Movement vectors changed by {angle:.1f}° between "
                                                "adjacent displacements."
                                            ),
                                        )
                                    )

                if joint is not None and prev_joint is not None:
                    if joint.confidence is not None and prev_joint.confidence is not None:
                        drop = prev_joint.confidence - joint.confidence
                        if drop > self.confidence_drop_threshold:
                            anomalies.append(
                                PotentialTrackingAnomaly(
                                    joint_name=joint_name,
                                    frame_index=frame_index,
                                    timestamp_seconds=frame.timestamp_seconds,
                                    anomaly_type="confidence_collapse",
                                    severity=drop,
                                    details=(
                                        f"Confidence dropped by {drop:.3f} between "
                                        "consecutive frames."
                                    ),
                                )
                            )

                previous_previous = previous
                previous = frame

        return anomalies

    def _worst_frames(
        self,
        recording: MovementRecording,
        anomalies: list[PotentialTrackingAnomaly],
    ) -> list[WorstFrameInspection]:
        by_frame: dict[int, list[str]] = defaultdict(list)
        for anomaly in anomalies:
            by_frame[anomaly.frame_index].append(anomaly.joint_name)

        worst: list[WorstFrameInspection] = []
        for frame_index, joint_names in sorted(
            by_frame.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )[:10]:
            frame = recording.frames[frame_index]
            affected = sorted(set(joint_names))
            confidence_values: dict[str, float] = {}
            visibility_values: dict[str, float] = {}
            for joint_name in affected:
                joint = frame.joints.get(joint_name)
                if joint is None:
                    continue
                if joint.confidence is not None:
                    confidence_values[joint_name] = float(joint.confidence)
                if joint.visibility is not None:
                    visibility_values[joint_name] = float(joint.visibility)

            anomaly_types = sorted(
                {
                    anomaly.anomaly_type
                    for anomaly in anomalies
                    if anomaly.frame_index == frame_index and anomaly.joint_name in affected
                }
            )
            worst.append(
                WorstFrameInspection(
                    swing_id=recording.recording_id,
                    frame_index=frame_index,
                    timestamp_seconds=frame.timestamp_seconds,
                    affected_joints=affected,
                    confidence_values=confidence_values,
                    visibility_values=visibility_values,
                    anomaly_types=anomaly_types,
                )
            )
        return worst

    def _arms_vs_legs_summary(
        self,
        joint_quality: dict[str, JointQualitySummary],
    ) -> ArmLegComparison:
        arm_stats: dict[str, float | int | str | None] = {}
        leg_stats: dict[str, float | int | str | None] = {}

        for group_name, group_joints in {"arms": ARM_JOINTS, "legs": LEG_JOINTS}.items():
            values = [
                joint_quality[joint_name]
                for joint_name in group_joints
                if joint_name in joint_quality
            ]
            if not values:
                continue
            detection_rates = [item.detection_rate for item in values]
            confidences = [
                item.mean_confidence
                for item in values
                if item.mean_confidence is not None
            ]
            low_confidence = [item.low_confidence_percentage for item in values]
            target = arm_stats if group_name == "arms" else leg_stats
            target["mean_detection_rate"] = sum(detection_rates) / len(detection_rates)
            target["mean_confidence"] = (
                sum(confidences) / len(confidences) if confidences else None
            )
            target["mean_low_confidence_percentage"] = (
                sum(low_confidence) / len(low_confidence) if low_confidence else None
            )
            target["joint_count"] = len(values)
            target["worst_joint"] = min(values, key=lambda item: item.detection_rate).joint_name

        return ArmLegComparison(arms=arm_stats, legs=leg_stats)

    def analyze_recording(self, recording: MovementRecording) -> PoseQualityReport:
        joint_quality = {
            joint_name: self._analyze_joint_quality(recording, joint_name)
            for joint_name in DEFAULT_JOINTS
        }
        temporal_quality = {
            joint_name: self._analyze_temporal_quality(recording, joint_name)
            for joint_name in DEFAULT_JOINTS
        }
        anomalies = self._detect_anomalies(recording)
        worst_frames = self._worst_frames(recording, anomalies)
        return PoseQualityReport(
            swing_id=recording.recording_id,
            total_frames=len(recording.frames),
            joint_quality=joint_quality,
            temporal_quality=temporal_quality,
            potential_tracking_anomalies=anomalies,
            worst_frames=worst_frames,
            arms_vs_legs=self._arms_vs_legs_summary(joint_quality),
        )

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def generate_analysis_artifacts(
        self,
        *,
        movement_recording: MovementRecording,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        report = self.analyze_recording(movement_recording)
        base_dir = Path(output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        quality_path = base_dir / "quality_summary.json"
        quality_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        joint_rows: list[dict[str, object]] = []
        for joint_name, joint_summary in report.joint_quality.items():
            joint_rows.append(
                {
                    "joint_name": joint_name,
                    "total_frames": joint_summary.total_frames,
                    "detected_frames": joint_summary.detected_frames,
                    "detection_rate": joint_summary.detection_rate,
                    "missing_frames": joint_summary.missing_frames,
                    "mean_confidence": joint_summary.mean_confidence,
                    "median_confidence": joint_summary.median_confidence,
                    "min_confidence": joint_summary.min_confidence,
                    "max_confidence": joint_summary.max_confidence,
                    "mean_visibility": joint_summary.mean_visibility,
                    "median_visibility": joint_summary.median_visibility,
                    "min_visibility": joint_summary.min_visibility,
                    "low_confidence_frames": joint_summary.low_confidence_frames,
                    "low_confidence_percentage": joint_summary.low_confidence_percentage,
                    "confidence_band": joint_summary.confidence_band,
                }
            )
        joint_csv_path = base_dir / "joint_quality.csv"
        self._write_csv(
            joint_csv_path,
            [
                "joint_name",
                "total_frames",
                "detected_frames",
                "detection_rate",
                "missing_frames",
                "mean_confidence",
                "median_confidence",
                "min_confidence",
                "max_confidence",
                "mean_visibility",
                "median_visibility",
                "min_visibility",
                "low_confidence_frames",
                "low_confidence_percentage",
                "confidence_band",
            ],
            joint_rows,
        )

        temporal_rows: list[dict[str, object]] = []
        for joint_name, temporal_summary in report.temporal_quality.items():
            temporal_rows.append(
                {
                    "joint_name": joint_name,
                    "low_confidence_frame_indices": (
                        temporal_summary.low_confidence_frame_indices
                    ),
                    "missing_detection_frame_indices": (
                        temporal_summary.missing_detection_frame_indices
                    ),
                    "low_confidence_periods": temporal_summary.low_confidence_periods,
                    "longest_low_confidence_period": (
                        temporal_summary.longest_low_confidence_period
                    ),
                    "affected_percentage": temporal_summary.affected_percentage,
                }
            )
        temporal_csv_path = base_dir / "temporal_quality.csv"
        self._write_csv(
            temporal_csv_path,
            [
                "joint_name",
                "low_confidence_frame_indices",
                "missing_detection_frame_indices",
                "low_confidence_periods",
                "longest_low_confidence_period",
                "affected_percentage",
            ],
            temporal_rows,
        )

        return {
            "quality_summary": quality_path,
            "joint_quality_csv": joint_csv_path,
            "temporal_quality_csv": temporal_csv_path,
        }

    @staticmethod
    def generate_summary_report_all(
        recordings: dict[str, MovementRecording],
        output_dir: str | Path,
    ) -> Path:
        base_dir = Path(output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = [
            "# Pose Quality Report",
            "",
            "## Scope",
            "",
            "This report analyzes the quality of existing pose estimation outputs "
            "without modifying the provider, smoothing, or data.",
            "",
            "## Thresholds",
            "",
            "- low_confidence_threshold = 0.3",
            "- acceptable_confidence_threshold = 0.5",
            "- high_confidence_threshold = 0.8",
            "",
        ]

        for swing_id, recording in recordings.items():
            service = PoseQualityAnalysisService()
            report = service.analyze_recording(recording)
            lines.append(f"## {swing_id}")
            lines.append("")
            lines.append(f"- total_frames: {report.total_frames}")
            for joint_name, joint_summary in report.joint_quality.items():
                mean_confidence = (
                    joint_summary.mean_confidence
                    if joint_summary.mean_confidence is not None
                    else "n/a"
                )
                lines.append(
                    f"- {joint_name}: detection_rate={joint_summary.detection_rate:.3f}, "
                    f"mean_confidence={mean_confidence}, "
                    f"low_confidence_percentage={joint_summary.low_confidence_percentage:.2f}%"
                )
            lines.append("")
            worst_joint = min(
                report.joint_quality.values(),
                key=lambda item: item.detection_rate,
            )
            lines.append(
                f"- lowest detection rate: {worst_joint.joint_name} "
                f"({worst_joint.detection_rate:.3f})"
            )
            lines.append("")

        report_path = base_dir / "pose_quality_report.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

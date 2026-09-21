from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import median

import cv2
import matplotlib
import numpy as np
from matplotlib import pyplot as plt

matplotlib.use("Agg")

from app.schemas.kinematics import AngleMetric, KinematicFrame, KinematicRecording, VelocityMetric
from app.schemas.movement import FramePose, JointObservation, MovementRecording

ANGLE_LABELS = [
    "left_elbow_angle",
    "right_elbow_angle",
    "left_knee_angle",
    "right_knee_angle",
]
VELOCITY_LABELS = [
    "left_wrist",
    "right_wrist",
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
]
SKELETON_CONNECTIONS: tuple[tuple[str, str], ...] = (
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
)

JOINT_COLORS = {
    "left_shoulder": (255, 0, 128),
    "right_shoulder": (255, 128, 0),
    "left_elbow": (0, 128, 255),
    "right_elbow": (0, 255, 128),
    "left_wrist": (128, 0, 255),
    "right_wrist": (255, 0, 255),
    "left_hip": (0, 255, 255),
    "right_hip": (255, 255, 0),
    "left_knee": (0, 128, 128),
    "right_knee": (128, 128, 0),
    "left_ankle": (0, 64, 255),
    "right_ankle": (255, 64, 0),
}


class InspectionService:
    @staticmethod
    def infer_fps_from_timestamps(frames: list[FramePose]) -> float | None:
        ordered = sorted(frames, key=lambda item: item.frame_index)
        if len(ordered) < 2:
            return None

        deltas: list[float] = []
        for earlier, current in zip(ordered, ordered[1:]):
            delta = current.timestamp_seconds - earlier.timestamp_seconds
            if delta > 0.0 and math.isfinite(delta):
                deltas.append(delta)

        if not deltas:
            return None

        median_delta = float(median(deltas))
        if median_delta <= 0.0 or not math.isfinite(median_delta):
            return None

        return 1.0 / median_delta

    @staticmethod
    def normalized_to_pixel(
        x: float | None,
        y: float | None,
        *,
        width: int,
        height: int,
    ) -> tuple[int, int] | None:
        if x is None or y is None:
            return None
        if width <= 0 or height <= 0:
            raise ValueError("Frame width and height must be positive integers.")
        safe_x = float(x)
        safe_y = float(y)
        if not math.isfinite(safe_x) or not math.isfinite(safe_y):
            return None
        clamped_x = max(0.0, min(1.0, safe_x))
        clamped_y = max(0.0, min(1.0, safe_y))
        pixel_x = int(round(clamped_x * width))
        pixel_y = int(round(clamped_y * height))
        return pixel_x, pixel_y

    @staticmethod
    def joint_is_renderable(joint: JointObservation | None) -> bool:
        if joint is None or not joint.detected:
            return False
        if joint.x is None or joint.y is None:
            return False
        if not math.isfinite(float(joint.x)) or not math.isfinite(float(joint.y)):
            return False
        return 0.0 <= float(joint.x) <= 1.0 and 0.0 <= float(joint.y) <= 1.0

    @staticmethod
    def skeleton_pair_is_eligible(
        frame: FramePose,
        *,
        start_joint: str,
        end_joint: str,
    ) -> bool:
        return (
            InspectionService.joint_is_renderable(frame.joints.get(start_joint))
            and InspectionService.joint_is_renderable(frame.joints.get(end_joint))
        )

    @staticmethod
    def angle_metric_is_renderable(
        metric: AngleMetric | None,
    ) -> bool:
        return bool(metric is not None and metric.valid and metric.value_degrees is not None)

    @staticmethod
    def render_joint_markers(
        image: np.ndarray,
        frame: FramePose,
        *,
        width: int,
        height: int,
        radius: int = 5,
    ) -> np.ndarray:
        for joint_name, joint in frame.joints.items():
            if not InspectionService.joint_is_renderable(joint):
                continue
            pixel = InspectionService.normalized_to_pixel(
                joint.x,
                joint.y,
                width=width,
                height=height,
            )
            if pixel is None:
                continue
            center = (int(pixel[0]), int(pixel[1]))
            color = JOINT_COLORS.get(joint_name, (255, 255, 255))
            cv2.circle(image, center, radius, color, -1)
            cv2.circle(image, center, radius + 2, (255, 255, 255), 1)
        return image

    @staticmethod
    def render_skeleton(
        image: np.ndarray,
        frame: FramePose,
        *,
        width: int,
        height: int,
        color: tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        for start_joint, end_joint in SKELETON_CONNECTIONS:
            if not InspectionService.skeleton_pair_is_eligible(
                frame,
                start_joint=start_joint,
                end_joint=end_joint,
            ):
                continue
            start = frame.joints[start_joint]
            end = frame.joints[end_joint]
            start_pixel = InspectionService.normalized_to_pixel(
                start.x,
                start.y,
                width=width,
                height=height,
            )
            end_pixel = InspectionService.normalized_to_pixel(
                end.x,
                end.y,
                width=width,
                height=height,
            )
            if start_pixel is None or end_pixel is None:
                continue
            cv2.line(image, start_pixel, end_pixel, color, thickness)
        return image

    @staticmethod
    def render_angle_annotations(
        image: np.ndarray,
        frame: FramePose,
        kinematic_frame: KinematicFrame | None,
        *,
        width: int,
        height: int,
    ) -> np.ndarray:
        if kinematic_frame is None:
            return image
        for metric_name in ANGLE_LABELS:
            metric = kinematic_frame.joint_angles.get(metric_name)
            if not InspectionService.angle_metric_is_renderable(metric):
                continue
            if metric is None or metric.value_degrees is None:
                continue
            annotation_joint_name = metric_name.replace("_angle", "")
            joint = frame.joints.get(annotation_joint_name)
            if joint is None or not InspectionService.joint_is_renderable(joint):
                continue
            pixel = InspectionService.normalized_to_pixel(
                joint.x,
                joint.y,
                width=width,
                height=height,
            )
            if pixel is None:
                continue
            label = f"{metric_name.replace('_', ' ')}: {metric.value_degrees:.1f}°"
            text_position = (pixel[0] + 10, max(15, pixel[1] - 10))
            cv2.putText(
                image,
                label,
                text_position,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        return image

    @staticmethod
    def render_raw_overlay(
        image: np.ndarray,
        frame: FramePose,
        *,
        width: int,
        height: int,
        as_ghost: bool = True,
    ) -> np.ndarray:
        color = (128, 128, 128) if as_ghost else (0, 165, 255)
        thickness = 1 if as_ghost else 2
        radius = 3 if as_ghost else 5
        for start_joint, end_joint in SKELETON_CONNECTIONS:
            s = frame.joints.get(start_joint)
            e = frame.joints.get(end_joint)
            if s is None or e is None:
                continue
            sx = s.raw_x if s.raw_x is not None else s.x
            sy = s.raw_y if s.raw_y is not None else s.y
            ex = e.raw_x if e.raw_x is not None else e.x
            ey = e.raw_y if e.raw_y is not None else e.y
            if sx is None or sy is None or ex is None or ey is None:
                continue
            sp = InspectionService.normalized_to_pixel(sx, sy, width=width, height=height)
            ep = InspectionService.normalized_to_pixel(ex, ey, width=width, height=height)
            if sp is not None and ep is not None:
                cv2.line(image, sp, ep, color, thickness)

        for joint in frame.joints.values():
            rx = joint.raw_x if joint.raw_x is not None else joint.x
            ry = joint.raw_y if joint.raw_y is not None else joint.y
            if rx is None or ry is None:
                continue
            p = InspectionService.normalized_to_pixel(rx, ry, width=width, height=height)
            if p is not None:
                cv2.circle(image, p, radius, color, -1)
        return image

    @staticmethod
    def render_metadata(
        image: np.ndarray,
        frame: FramePose,
        *,
        mode: str = "FILTERED",
    ) -> np.ndarray:
        cv2.putText(
            image,
            f"frame_index={frame.frame_index}  mode={mode}",
            (12, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            f"timestamp_seconds={frame.timestamp_seconds:.3f}s",
            (12, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        return image

    @staticmethod
    def render_frame_overlay(
        *,
        image: np.ndarray,
        movement_frame: FramePose,
        kinematic_frame: KinematicFrame | None,
        mode: str = "FILTERED",
    ) -> np.ndarray:
        height, width = image.shape[:2]
        if mode in ("RAW", "RAW+FILTERED"):
            image = InspectionService.render_raw_overlay(
                image,
                movement_frame,
                width=width,
                height=height,
                as_ghost=(mode == "RAW+FILTERED"),
            )
        if mode in ("FILTERED", "RAW+FILTERED"):
            image = InspectionService.render_skeleton(
                image, movement_frame, width=width, height=height
            )
            image = InspectionService.render_joint_markers(
                image,
                movement_frame,
                width=width,
                height=height,
            )
        image = InspectionService.render_angle_annotations(
            image,
            movement_frame,
            kinematic_frame,
            width=width,
            height=height,
        )
        image = InspectionService.render_metadata(image, movement_frame, mode=mode)
        return image

    @staticmethod
    def validate_timestamp_order(frames: list[FramePose]) -> tuple[bool, list[str]]:
        issues: list[str] = []
        previous_timestamp: float | None = None
        for frame in sorted(frames, key=lambda item: item.frame_index):
            if (
                previous_timestamp is not None
                and frame.timestamp_seconds < previous_timestamp
            ):
                issues.append(
                    "Frame "
                    f"{frame.frame_index} timestamp_seconds="
                    f"{frame.timestamp_seconds:.6f}s is earlier than the prior "
                    f"value {previous_timestamp:.6f}s."
                )
            previous_timestamp = frame.timestamp_seconds
        return not issues, issues

    @staticmethod
    def build_quality_summary(
        movement: MovementRecording,
        kinematic: KinematicRecording,
    ) -> dict[str, object]:
        total_frames = len(movement.frames)
        metrics: dict[str, dict[str, object]] = {}
        invalid_reasons: dict[str, int] = {}
        for metric_name in ANGLE_LABELS:
            valid_count = 0
            invalid_count = 0
            angle_reasons: dict[str, int] = {}
            for frame in kinematic.frames:
                angle_metric: AngleMetric | None = frame.joint_angles.get(metric_name)
                if angle_metric is None:
                    invalid_count += 1
                    angle_reasons["missing_metric"] = angle_reasons.get("missing_metric", 0) + 1
                    continue
                if angle_metric.valid and angle_metric.value_degrees is not None:
                    valid_count += 1
                else:
                    invalid_count += 1
                    reason = angle_metric.reason or "invalid_metric"
                    angle_reasons[reason] = angle_reasons.get(reason, 0) + 1
            metrics[metric_name] = {
                "valid_frames": valid_count,
                "invalid_frames": invalid_count,
                "validity_percentage": (
                    (valid_count / total_frames * 100.0) if total_frames else 0.0
                ),
                "invalid_reasons": angle_reasons,
            }
            for reason, count in angle_reasons.items():
                invalid_reasons[f"{metric_name}:{reason}"] = count

        for joint_name in VELOCITY_LABELS:
            valid_count = 0
            invalid_count = 0
            velocity_reasons: dict[str, int] = {}
            for frame in kinematic.frames:
                velocity_metric: VelocityMetric | None = frame.linear_velocities.get(joint_name)
                if velocity_metric is None:
                    invalid_count += 1
                    velocity_reasons["missing_metric"] = (
                        velocity_reasons.get("missing_metric", 0) + 1
                    )
                    continue
                if (
                    velocity_metric.valid
                    and velocity_metric.value_normalized_units_per_second is not None
                ):
                    valid_count += 1
                else:
                    invalid_count += 1
                    reason = velocity_metric.reason or "invalid_metric"
                    velocity_reasons[reason] = velocity_reasons.get(reason, 0) + 1
            metrics[f"{joint_name}_velocity"] = {
                "valid_frames": valid_count,
                "invalid_frames": invalid_count,
                "validity_percentage": (
                    (valid_count / total_frames * 100.0) if total_frames else 0.0
                ),
                "invalid_reasons": velocity_reasons,
            }
            for reason, count in velocity_reasons.items():
                invalid_reasons[f"{joint_name}_velocity:{reason}"] = count

        return {
            "video_id": movement.source_video_id,
            "total_frames": total_frames,
            "metrics": metrics,
            "invalidity_reasons": invalid_reasons,
        }

    @staticmethod
    def render_temporal_plots(
        *,
        kinematic: KinematicRecording,
        output_dir: str | Path,
    ) -> tuple[Path, Path]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamps = [frame.timestamp_seconds for frame in kinematic.frames]

        angle_path = output_path / "joint_angles.png"
        plt.figure(figsize=(10, 5))
        for metric_name in ANGLE_LABELS:
            values = []
            for frame in kinematic.frames:
                angle_metric: AngleMetric | None = frame.joint_angles.get(metric_name)
                values.append(
                    angle_metric.value_degrees
                    if (
                        angle_metric is not None
                        and angle_metric.valid
                        and angle_metric.value_degrees is not None
                    )
                    else float("nan")
                )
            plt.plot(timestamps, values, label=metric_name)
        plt.xlabel("timestamp_seconds")
        plt.ylabel("degrees")
        plt.title("Joint angles over time")
        plt.legend()
        plt.tight_layout()
        plt.savefig(angle_path)
        plt.close()

        velocity_path = output_path / "linear_velocities.png"
        plt.figure(figsize=(10, 5))
        for joint_name in VELOCITY_LABELS:
            values = []
            for frame in kinematic.frames:
                velocity_metric: VelocityMetric | None = frame.linear_velocities.get(joint_name)
                values.append(
                    velocity_metric.value_normalized_units_per_second
                    if (
                        velocity_metric is not None
                        and velocity_metric.valid
                        and velocity_metric.value_normalized_units_per_second is not None
                    )
                    else float("nan")
                )
            plt.plot(timestamps, values, label=f"{joint_name}_velocity")
        plt.xlabel("timestamp_seconds")
        plt.ylabel("normalized_units_per_second")
        plt.title("Linear velocity over time")
        plt.legend()
        plt.tight_layout()
        plt.savefig(velocity_path)
        plt.close()

        return angle_path, velocity_path

    @staticmethod
    def render_overlay_video(
        *,
        movement: MovementRecording,
        kinematic: KinematicRecording,
        extracted_frames_dir: str | Path,
        output_path: str | Path,
        mode: str = "FILTERED",
    ) -> Path:
        frame_dir = Path(extracted_frames_dir)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not frame_dir.exists():
            raise FileNotFoundError(f"Extracted frames directory not found: {frame_dir}")

        fps = (
            movement.fps
            if movement.fps is not None
            else InspectionService.infer_fps_from_timestamps(movement.frames)
        )
        if fps is None or fps <= 0.0:
            raise ValueError(
                "Cannot determine the source FPS for the overlay video from "
                "movement metadata or timestamps."
            )
        frame_files = sorted(frame_dir.glob("*.png"))
        if not frame_files:
            raise FileNotFoundError(f"No extracted frame PNGs found in {frame_dir}")

        first_image = cv2.imread(str(frame_files[0]), cv2.IMREAD_COLOR)
        if first_image is None:
            raise FileNotFoundError(f"Could not read sample frame: {frame_files[0]}")
        height, width = first_image.shape[:2]

        fourcc = 0x7634706D
        video_writer = cv2.VideoWriter(
            str(target),
            fourcc,
            fps,
            (width, height),
        )
        if not video_writer.isOpened():
            raise RuntimeError(f"Unable to create overlay video at {target}")

        try:
            for frame_file in frame_files:
                frame_index = int(frame_file.stem.rsplit("_", 1)[-1])
                movement_frame = next(
                    (item for item in movement.frames if item.frame_index == frame_index),
                    None,
                )
                kinematic_frame = next(
                    (item for item in kinematic.frames if item.frame_index == frame_index),
                    None,
                )
                image = cv2.imread(str(frame_file), cv2.IMREAD_COLOR)
                if image is None:
                    continue
                if movement_frame is not None:
                    image = InspectionService.render_frame_overlay(
                        image=image,
                        movement_frame=movement_frame,
                        kinematic_frame=kinematic_frame,
                        mode=mode,
                    )
                video_writer.write(image)
        finally:
            video_writer.release()
        return target

    @staticmethod
    def generate_inspection_bundle(
        *,
        movement: MovementRecording,
        kinematic: KinematicRecording,
        extracted_frames_dir: str | Path,
        output_dir: str | Path,
        mode: str = "FILTERED",
    ) -> dict[str, Path | str]:
        base_dir = Path(output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        quality_summary = InspectionService.build_quality_summary(movement, kinematic)
        quality_summary_path = base_dir / "quality_summary.json"
        quality_summary_path.write_text(json.dumps(quality_summary, indent=2), encoding="utf-8")

        frame_dir = base_dir / "overlay_frames"
        frame_dir.mkdir(parents=True, exist_ok=True)
        for frame in sorted(movement.frames, key=lambda item: item.frame_index):
            frame_file = Path(extracted_frames_dir) / f"frame_{frame.frame_index:06d}.png"
            if not frame_file.exists():
                continue
            image = cv2.imread(str(frame_file), cv2.IMREAD_COLOR)
            if image is None:
                continue
            kinematic_frame = next(
                (item for item in kinematic.frames if item.frame_index == frame.frame_index),
                None,
            )
            annotated = InspectionService.render_frame_overlay(
                image=image,
                movement_frame=frame,
                kinematic_frame=kinematic_frame,
                mode=mode,
            )
            cv2.imwrite(str(frame_dir / f"frame_{frame.frame_index:06d}.png"), annotated)

        overlay_video = base_dir / "overlay_video.mp4"
        InspectionService.render_overlay_video(
            movement=movement,
            kinematic=kinematic,
            extracted_frames_dir=extracted_frames_dir,
            output_path=overlay_video,
            mode=mode,
        )

        angle_path, velocity_path = InspectionService.render_temporal_plots(
            kinematic=kinematic,
            output_dir=base_dir,
        )

        return {
            "quality_summary": quality_summary_path,
            "overlay_frames": frame_dir,
            "overlay_video": overlay_video,
            "joint_angles_plot": angle_path,
            "linear_velocity_plot": velocity_path,
        }

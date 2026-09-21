from __future__ import annotations

import math
from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np
from app.schemas.bat import BatDetection, BatTrackingResult, BatTrajectoryPoint
from app.schemas.movement import MovementRecording


class BaseBatTracker(ABC):
    """Abstract interface for bat tracking algorithms."""

    @abstractmethod
    def track(
        self,
        video_id: str,
        frames_dir: Path | None = None,
        movement: MovementRecording | None = None,
    ) -> BatTrackingResult:
        """Track the bat across frames and return BatTrackingResult."""
        ...


class ShaftEdgeBatTracker(BaseBatTracker):
    """Bat tracker using edge gradient analysis, line detection,

    kinematic continuity, and optional hand anchor priors.
    """

    def __init__(
        self,
        min_line_length_ratio: float = 0.08,
        max_line_length_ratio: float = 0.45,
        canny_thresh1: int = 50,
        canny_thresh2: int = 150,
        hough_threshold: int = 35,
    ) -> None:
        self.min_line_length_ratio = min_line_length_ratio
        self.max_line_length_ratio = max_line_length_ratio
        self.canny_thresh1 = canny_thresh1
        self.canny_thresh2 = canny_thresh2
        self.hough_threshold = hough_threshold

    @staticmethod
    def _calculate_angle_deg(p1: tuple[float, float], p2: tuple[float, float]) -> float:
        """Calculate angle in degrees from p1 to p2 relative to positive horizontal x-axis."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        rad = math.atan2(dy, dx)
        deg = math.degrees(rad) % 360.0
        return deg

    @staticmethod
    def compute_sweet_spot(
        handle: tuple[float, float],
        barrel: tuple[float, float],
        ratio: float = 0.75,
    ) -> tuple[float, float]:
        """Compute sweet spot location ~75% along shaft from handle toward barrel."""
        return (
            handle[0] + ratio * (barrel[0] - handle[0]),
            handle[1] + ratio * (barrel[1] - handle[1]),
        )

    def detect_in_image(
        self,
        image_path: Path,
        hand_anchor: tuple[float, float] | None = None,
    ) -> tuple[tuple[float, float], tuple[float, float], float] | None:
        """Detect bat shaft in a single frame image.

        Returns ((handle_x, handle_y), (barrel_x, barrel_y), confidence)
        in normalized coords [0, 1].
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return None

        h, w = img.shape[:2]
        diag = math.hypot(w, h)
        min_px = int(self.min_line_length_ratio * diag)
        max_px = int(self.max_line_length_ratio * diag)

        # Grayscale and edge detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_thresh1, self.canny_thresh2)

        # Region of interest around hand anchor if available
        if hand_anchor is not None:
            mask = np.zeros_like(edges)
            cx, cy = int(hand_anchor[0] * w), int(hand_anchor[1] * h)
            roi_r = int(0.40 * diag)
            cv2.circle(mask, (cx, cy), roi_r, 255, -1)
            edges = cv2.bitwise_and(edges, mask)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180.0,
            threshold=self.hough_threshold,
            minLineLength=min_px,
            maxLineGap=20,
        )

        if lines is None or len(lines) == 0:
            return None

        best_score = -1.0
        best_pts: tuple[tuple[float, float], tuple[float, float]] | None = None

        for line in lines:
            pts = line.reshape(-1)
            if len(pts) < 4:
                continue
            x1, y1, x2, y2 = int(pts[0]), int(pts[1]), int(pts[2]), int(pts[3])
            length = math.hypot(x2 - x1, y2 - y1)
            if length < min_px or length > max_px:
                continue

            # Convert to normalized
            p1 = (x1 / w, y1 / h)
            p2 = (x2 / w, y2 / h)

            score = length / max_px

            if hand_anchor is not None:
                d1 = math.hypot(p1[0] - hand_anchor[0], p1[1] - hand_anchor[1])
                d2 = math.hypot(p2[0] - hand_anchor[0], p2[1] - hand_anchor[1])
                dist_to_hand = min(d1, d2)
                # Score increases if one endpoint is near hand
                proximity_score = max(0.0, 1.0 - dist_to_hand * 3.0)
                score = 0.5 * score + 0.5 * proximity_score

                # Order so handle is closer to hand
                if d1 > d2:
                    p1, p2 = p2, p1

            if score > best_score:
                best_score = score
                best_pts = (p1, p2)

        if best_pts is not None and best_score >= 0.20:
            return (best_pts[0], best_pts[1], float(min(1.0, best_score)))

        return None

    def track(
        self,
        video_id: str,
        frames_dir: Path | None = None,
        movement: MovementRecording | None = None,
    ) -> BatTrackingResult:
        """Run bat tracking across frames."""
        detections: list[BatDetection] = []

        total_frames = 0
        timestamps: dict[int, float] = {}
        hand_anchors: dict[int, tuple[float, float]] = {}

        if movement is not None:
            total_frames = len(movement.frames)
            for f in movement.frames:
                timestamps[f.frame_index] = f.timestamp_seconds
                # Extract hands position as prior anchor
                rw = f.joints.get("right_wrist")
                lw = f.joints.get("left_wrist")
                valid_pts: list[tuple[float, float]] = []
                for j in (rw, lw):
                    if j is not None and getattr(j, "detected", True):
                        jx = getattr(j, "x", None)
                        jy = getattr(j, "y", None)
                        if jx is not None and jy is not None:
                            valid_pts.append((float(jx), float(jy)))
                if valid_pts:
                    avg_x = sum(p[0] for p in valid_pts) / len(valid_pts)
                    avg_y = sum(p[1] for p in valid_pts) / len(valid_pts)
                    hand_anchors[f.frame_index] = (avg_x, avg_y)

        # If frames directory is present, inspect images
        image_files: list[Path] = []
        if frames_dir is not None and frames_dir.exists():
            image_files = sorted(
                list(frames_dir.glob("*.jpg")) + list(frames_dir.glob("*.png")),
                key=lambda p: int("".join(filter(str.isdigit, p.stem)) or "0"),
            )
            if total_frames == 0:
                total_frames = len(image_files)

        for idx in range(total_frames):
            ts = timestamps.get(idx, float(idx) * (1.0 / 30.0))
            anchor = hand_anchors.get(idx)

            detection = BatDetection(
                frame_index=idx,
                timestamp_seconds=ts,
                detected=False,
            )

            if idx < len(image_files):
                res = self.detect_in_image(image_files[idx], hand_anchor=anchor)
                if res is not None:
                    handle, barrel, conf = res
                    angle = self._calculate_angle_deg(handle, barrel)
                    sweet = self.compute_sweet_spot(handle, barrel)
                    length = math.hypot(barrel[0] - handle[0], barrel[1] - handle[1])

                    detection = BatDetection(
                        frame_index=idx,
                        timestamp_seconds=ts,
                        detected=True,
                        handle_point=handle,
                        barrel_point=barrel,
                        sweet_spot=sweet,
                        shaft_orientation_deg=angle,
                        confidence=conf,
                        length_normalized=length,
                    )

            detections.append(detection)

        # Temporal gap filling (up to 3 frames)
        self._interpolate_short_gaps(detections)

        # Build kinematics trajectory
        trajectory = self._build_trajectory(detections)

        # Compute summary metrics
        detected_count = sum(1 for d in detections if d.detected)
        coverage = detected_count / max(1, total_frames)

        peak_speed = None
        peak_speed_frame = None
        contact_frame = None
        attack_angle = None

        valid_speeds = [
            (t.frame_index, t.barrel_speed)
            for t in trajectory
            if t.barrel_speed is not None
        ]
        if valid_speeds:
            best_speed = max(valid_speeds, key=lambda item: item[1] or 0.0)
            peak_speed_frame = best_speed[0]
            peak_speed = best_speed[1]

            # In typical swings, impact occurs around peak barrel speed
            # or initial deceleration inflection
            contact_frame = peak_speed_frame

            # Compute attack angle at contact: slope of barrel vector (-dy, dx)
            attack_angle = self._calculate_attack_angle(trajectory, contact_frame)

        return BatTrackingResult(
            video_id=video_id,
            total_frames=total_frames,
            detected_frames_count=detected_count,
            tracking_coverage=coverage,
            detections=detections,
            trajectory=trajectory,
            peak_barrel_speed=peak_speed,
            peak_barrel_speed_frame=peak_speed_frame,
            estimated_contact_frame=contact_frame,
            attack_angle_at_contact_deg=attack_angle,
        )

    def _interpolate_short_gaps(self, detections: list[BatDetection], max_gap: int = 3) -> None:
        """Fill short missing detection gaps with linear interpolation."""
        n = len(detections)
        i = 0
        while i < n:
            if not detections[i].detected:
                start = i - 1
                while i < n and not detections[i].detected:
                    i += 1
                end = i
                gap_len = end - (start + 1)
                if start >= 0 and end < n and gap_len <= max_gap:
                    p_start = detections[start]
                    p_end = detections[end]
                    if (
                        p_start.handle_point
                        and p_start.barrel_point
                        and p_end.handle_point
                        and p_end.barrel_point
                    ):
                        for k in range(1, gap_len + 1):
                            idx = start + k
                            alpha = k / (gap_len + 1)
                            h_interp = (
                                p_start.handle_point[0]
                                + alpha * (p_end.handle_point[0] - p_start.handle_point[0]),
                                p_start.handle_point[1]
                                + alpha * (p_end.handle_point[1] - p_start.handle_point[1]),
                            )
                            b_interp = (
                                p_start.barrel_point[0]
                                + alpha * (p_end.barrel_point[0] - p_start.barrel_point[0]),
                                p_start.barrel_point[1]
                                + alpha * (p_end.barrel_point[1] - p_start.barrel_point[1]),
                            )
                            angle = self._calculate_angle_deg(h_interp, b_interp)
                            sweet = self.compute_sweet_spot(h_interp, b_interp)
                            detections[idx].detected = True
                            detections[idx].handle_point = h_interp
                            detections[idx].barrel_point = b_interp
                            detections[idx].sweet_spot = sweet
                            detections[idx].shaft_orientation_deg = angle
                            detections[idx].confidence = 0.5 * (
                                p_start.confidence + p_end.confidence
                            )
                            detections[idx].length_normalized = math.hypot(
                                b_interp[0] - h_interp[0], b_interp[1] - h_interp[1]
                            )
            else:
                i += 1

    def _build_trajectory(self, detections: list[BatDetection]) -> list[BatTrajectoryPoint]:
        """Compute barrel speeds and angular velocities between consecutive frames."""
        trajectory: list[BatTrajectoryPoint] = []
        for i, curr in enumerate(detections):
            barrel_pos = curr.barrel_point if curr.detected else None
            shaft_angle = curr.shaft_orientation_deg if curr.detected else None

            speed = None
            angular_velocity = None

            if i > 0 and curr.detected and detections[i - 1].detected:
                prev = detections[i - 1]
                dt = curr.timestamp_seconds - prev.timestamp_seconds
                if dt > 0 and curr.barrel_point and prev.barrel_point:
                    dist = math.hypot(
                        curr.barrel_point[0] - prev.barrel_point[0],
                        curr.barrel_point[1] - prev.barrel_point[1],
                    )
                    speed = dist / dt

                has_angles = (
                    curr.shaft_orientation_deg is not None
                    and prev.shaft_orientation_deg is not None
                )
                if dt > 0 and has_angles:
                    assert curr.shaft_orientation_deg is not None
                    assert prev.shaft_orientation_deg is not None
                    d_angle = abs(curr.shaft_orientation_deg - prev.shaft_orientation_deg) % 360.0
                    if d_angle > 180.0:
                        d_angle = 360.0 - d_angle
                    angular_velocity = d_angle / dt

            trajectory.append(
                BatTrajectoryPoint(
                    frame_index=curr.frame_index,
                    timestamp_seconds=curr.timestamp_seconds,
                    barrel_position=barrel_pos,
                    barrel_speed=speed,
                    shaft_angle_deg=shaft_angle,
                    angular_velocity_deg_s=angular_velocity,
                )
            )
        return trajectory

    def _calculate_attack_angle(
        self,
        trajectory: list[BatTrajectoryPoint],
        contact_frame: int,
    ) -> float | None:
        """Calculate vertical attack angle (in degrees) of barrel around impact.

        Positive angle indicates upward trajectory into ball, negative indicates chopping down.
        """
        if contact_frame <= 0 or contact_frame >= len(trajectory):
            return None

        p_curr = trajectory[contact_frame].barrel_position
        p_prev = trajectory[contact_frame - 1].barrel_position

        if p_curr is None or p_prev is None:
            return None

        dx = p_curr[0] - p_prev[0]
        # In image coords, y increases downwards, so vertical upward movement is -dy
        dy = -(p_curr[1] - p_prev[1])

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return 0.0

        angle_rad = math.atan2(dy, abs(dx))  # relative to swing forward direction
        return math.degrees(angle_rad)

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

    @staticmethod
    def _interpolate_short_gaps(detections: list[BatDetection], max_gap: int = 3) -> None:
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
                if 0 < gap_len <= max_gap and start >= 0 and end < n:
                    p_start = detections[start]
                    p_end = detections[end]
                    if (
                        p_start.detected
                        and p_end.detected
                        and p_start.handle_point
                        and p_end.handle_point
                        and p_start.barrel_point
                        and p_end.barrel_point
                    ):
                        for k in range(start + 1, end):
                            alpha = float(k - start) / float(end - start)
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
                            angle = BaseBatTracker._calculate_angle_deg(h_interp, b_interp)
                            sweet = BaseBatTracker.compute_sweet_spot(h_interp, b_interp)
                            detections[k].detected = True
                            detections[k].handle_point = h_interp
                            detections[k].barrel_point = b_interp
                            detections[k].sweet_spot = sweet
                            detections[k].shaft_orientation_deg = angle
                            detections[k].confidence = 0.5 * (
                                (p_start.confidence or 0.5) + (p_end.confidence or 0.5)
                            )
                            detections[k].length_normalized = math.hypot(
                                b_interp[0] - h_interp[0], b_interp[1] - h_interp[1]
                            )
            else:
                i += 1

    @staticmethod
    def _build_trajectory(detections: list[BatDetection]) -> list[BatTrajectoryPoint]:
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

    @staticmethod
    def _calculate_attack_angle(
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
        dy = -(p_curr[1] - p_prev[1])

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return 0.0

        angle_rad = math.atan2(dy, abs(dx))
        return math.degrees(angle_rad)


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

COLOR_PRESETS: dict[str, dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
    "neon_green_orange": {
        "barrel": ((35, 70, 70), (85, 255, 255)),   # Neon Green / Lime
        "handle": ((5, 100, 100), (22, 255, 255)),  # Neon Orange
    },
    "neon_orange_green": {
        "barrel": ((5, 100, 100), (22, 255, 255)),  # Neon Orange
        "handle": ((35, 70, 70), (85, 255, 255)),   # Neon Green
    },
    "yellow_pink": {
        "barrel": ((22, 90, 90), (36, 255, 255)),   # Neon Yellow
        "handle": ((140, 80, 80), (170, 255, 255)), # Hot Pink / Magenta
    },
}


class ColorMarkerBatTracker(BaseBatTracker):
    """Bat tracker using high-contrast HSV chromatic segmentation.

    Detects optical color markers placed on the barrel and handle/knob of the bat.
    Immune to high-velocity motion blur and invariant to background edge noise.
    """

    def __init__(
        self,
        color_preset: str = "neon_green_orange",
        custom_barrel_range: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None,
        custom_handle_range: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None,
        min_blob_area_px: int = 10,
        max_bat_length_ratio: float = 0.75,
        min_bat_length_ratio: float = 0.03,
    ) -> None:
        self.color_preset = color_preset
        preset = COLOR_PRESETS.get(color_preset, COLOR_PRESETS["neon_green_orange"])
        self.barrel_range = custom_barrel_range or preset["barrel"]
        self.handle_range = custom_handle_range or preset["handle"]
        self.min_blob_area_px = min_blob_area_px
        self.max_bat_length_ratio = max_bat_length_ratio
        self.min_bat_length_ratio = min_bat_length_ratio

    def _find_marker_centroid(
        self,
        hsv: np.ndarray,
        lower: tuple[int, int, int],
        upper: tuple[int, int, int],
        roi_center: tuple[float, float] | None = None,
        roi_radius_ratio: float | None = None,
    ) -> tuple[tuple[float, float], float] | None:
        h, w = hsv.shape[:2]
        diag = math.hypot(w, h)

        lower_np = np.array(lower, dtype=np.uint8)
        upper_np = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_np, upper_np)

        if roi_center is not None and roi_radius_ratio is not None:
            roi_mask = np.zeros_like(mask)
            cx, cy = int(roi_center[0] * w), int(roi_center[1] * h)
            r = int(roi_radius_ratio * diag)
            cv2.circle(roi_mask, (cx, cy), max(15, r), 255, -1)
            mask = cv2.bitwise_and(mask, roi_mask)

        # Morphological noise removal
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        best_cnt = contours[0]
        area = cv2.contourArea(best_cnt)
        if area < self.min_blob_area_px:
            return None

        m = cv2.moments(best_cnt)
        if m["m00"] <= 0:
            return None

        cx_px = m["m10"] / m["m00"]
        cy_px = m["m01"] / m["m00"]
        norm_x = cx_px / w
        norm_y = cy_px / h

        conf = float(min(1.0, max(0.55, area / 200.0)))
        return ((norm_x, norm_y), conf)

    def detect_in_image(
        self,
        image_input: Path | str | np.ndarray,
        hand_anchor: tuple[float, float] | None = None,
    ) -> tuple[tuple[float, float], tuple[float, float], float] | None:
        """Detect colored markers on the bat in a single frame.

        Returns ((handle_x, handle_y), (barrel_x, barrel_y), confidence).
        """
        img: np.ndarray | None
        if isinstance(image_input, np.ndarray):
            img = image_input
        else:
            img = cv2.imread(str(image_input))
        if img is None:
            return None

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 1. Search handle marker (prioritize region near hand anchor if known)
        handle_res = self._find_marker_centroid(
            hsv,
            self.handle_range[0],
            self.handle_range[1],
            roi_center=hand_anchor,
            roi_radius_ratio=0.35 if hand_anchor else None,
        )

        # 2. Search barrel marker
        barrel_res = self._find_marker_centroid(
            hsv,
            self.barrel_range[0],
            self.barrel_range[1],
            roi_center=hand_anchor,
            roi_radius_ratio=0.65 if hand_anchor else None,
        )

        if handle_res is not None and barrel_res is not None:
            handle_pt, h_conf = handle_res
            barrel_pt, b_conf = barrel_res
            length = math.hypot(barrel_pt[0] - handle_pt[0], barrel_pt[1] - handle_pt[1])
            if self.min_bat_length_ratio <= length <= self.max_bat_length_ratio:
                conf = min(0.98, float(0.5 * (h_conf + b_conf) + 0.15))
                return (handle_pt, barrel_pt, conf)

        if barrel_res is not None and hand_anchor is not None:
            barrel_pt, b_conf = barrel_res
            length = math.hypot(barrel_pt[0] - hand_anchor[0], barrel_pt[1] - hand_anchor[1])
            if self.min_bat_length_ratio <= length <= self.max_bat_length_ratio:
                conf = min(0.85, float(b_conf * 0.85))
                return (hand_anchor, barrel_pt, conf)

        return None

    def track(
        self,
        video_id: str,
        frames_dir: Path | None = None,
        movement: MovementRecording | None = None,
    ) -> BatTrackingResult:
        """Run color marker bat tracking across video frames."""
        detections: list[BatDetection] = []
        total_frames = 0
        timestamps: dict[int, float] = {}
        hand_anchors: dict[int, tuple[float, float]] = {}

        if movement is not None:
            total_frames = len(movement.frames)
            for f in movement.frames:
                timestamps[f.frame_index] = f.timestamp_seconds
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

        self._interpolate_short_gaps(detections)
        trajectory = self._build_trajectory(detections)

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
            contact_frame = peak_speed_frame
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


class HybridBatTracker(BaseBatTracker):
    """Hybrid bat tracker combining high-precision color markers with edge detection fallback."""

    def __init__(
        self,
        color_preset: str = "neon_green_orange",
        custom_barrel_range: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None,
        custom_handle_range: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None,
        edge_fallback: bool = True,
    ) -> None:
        self.color_tracker = ColorMarkerBatTracker(
            color_preset=color_preset,
            custom_barrel_range=custom_barrel_range,
            custom_handle_range=custom_handle_range,
        )
        self.edge_tracker = ShaftEdgeBatTracker() if edge_fallback else None

    def track(
        self,
        video_id: str,
        frames_dir: Path | None = None,
        movement: MovementRecording | None = None,
    ) -> BatTrackingResult:
        color_result = self.color_tracker.track(
            video_id=video_id,
            frames_dir=frames_dir,
            movement=movement,
        )

        min_threshold = max(3, int(color_result.total_frames * 0.15))
        if color_result.detected_frames_count >= min_threshold or self.edge_tracker is None:
            # Color markers were present, fill missing frames with edge tracker if enabled
            if (
                self.edge_tracker is not None
                and color_result.detected_frames_count < color_result.total_frames
            ):
                edge_result = self.edge_tracker.track(
                    video_id=video_id,
                    frames_dir=frames_dir,
                    movement=movement,
                )
                for idx, det in enumerate(color_result.detections):
                    if not det.detected and idx < len(edge_result.detections):
                        e_det = edge_result.detections[idx]
                        if e_det.detected:
                            color_result.detections[idx] = e_det

                self._interpolate_short_gaps(color_result.detections)
                color_result.trajectory = self._build_trajectory(color_result.detections)
                color_result.detected_frames_count = sum(
                    1 for d in color_result.detections if d.detected
                )
                color_result.tracking_coverage = (
                    color_result.detected_frames_count / max(1, color_result.total_frames)
                )

            return color_result

        # Color markers absent: fallback to edge detector
        return self.edge_tracker.track(
            video_id=video_id,
            frames_dir=frames_dir,
            movement=movement,
        )

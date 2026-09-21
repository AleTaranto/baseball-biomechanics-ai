from __future__ import annotations

import math

from app.schemas.movement import (
    DEFAULT_JOINTS,
    FramePose,
    JointObservation,
    MovementRecording,
)


class OneEuroFilter:
    """One-Euro filter for low-latency, adaptive smoothing of noisy tracking signals.

    Reference: Casiez et al., "1€ Filter: A Simple Speed-based Low-pass Filter for Noisy
    Input in Human-Computer Interaction", CHI 2012.
    """

    def __init__(
        self,
        *,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev: float | None = None
        self.dx_prev: float = 0.0
        self.t_prev: float | None = None

    def _smoothing_factor(self, dt: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * dt
        return r / (r + 1.0)

    def filter(self, x: float, timestamp: float) -> float:
        if self.t_prev is None or self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0.0
            self.t_prev = timestamp
            return x

        dt = timestamp - self.t_prev
        if dt <= 0.0 or not math.isfinite(dt):
            # Same timestamp or non-positive dt: maintain current estimate
            return self.x_prev

        # Estimate derivative and smooth it
        dx = (x - self.x_prev) / dt
        a_d = self._smoothing_factor(dt, self.d_cutoff)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        # Adaptive cutoff frequency based on movement speed
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._smoothing_factor(dt, cutoff)
        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = timestamp
        return x_hat

    def reset(self) -> None:
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None


class TemporalFilteringService:
    """Stabilizes kinematic joint trajectories without oversmoothing high-speed movement."""

    def __init__(
        self,
        *,
        min_cutoff: float = 1.0,
        beta: float = 1.5,
        d_cutoff: float = 1.0,
        max_gap_frames: int = 3,
        max_velocity_threshold: float = 15.0,  # normalized units per second
        min_confidence_threshold: float = 0.2,
    ) -> None:
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.max_gap_frames = int(max_gap_frames)
        self.max_velocity_threshold = float(max_velocity_threshold)
        self.min_confidence_threshold = float(min_confidence_threshold)

    def filter_recording(
        self,
        recording: MovementRecording,
        *,
        interpolate_gaps: bool = True,
        reject_outliers: bool = True,
    ) -> MovementRecording:
        """Return a stabilized clone of the movement recording, preserving original raw values."""
        cloned = recording.model_copy(deep=True)
        cloned.filter_status = "filtered"

        frames = cloned.frames
        if len(frames) < 2:
            return cloned

        # 1. Step 1: Outlier rejection & confidence gating
        if reject_outliers:
            self._detect_outliers(frames)

        # 2. Step 2: Micro-gap interpolation
        if interpolate_gaps:
            self._interpolate_short_gaps(frames)

        # 3. Step 3: One-Euro temporal smoothing
        self._apply_one_euro_filter(frames)

        return cloned

    def _detect_outliers(self, frames: list[FramePose]) -> None:
        for joint_name in DEFAULT_JOINTS:
            prev_valid: tuple[float, float, float] | None = None  # (x, y, t)
            for frame in frames:
                joint = frame.joints.get(joint_name)
                if joint is None or not joint.detected or joint.x is None or joint.y is None:
                    continue

                # Preserve raw values if not already preserved
                if joint.raw_x is None:
                    joint.raw_x = joint.x
                if joint.raw_y is None:
                    joint.raw_y = joint.y
                if joint.raw_z is None:
                    joint.raw_z = joint.z

                # Low confidence check
                low_conf = (
                    joint.confidence is not None
                    and joint.confidence < self.min_confidence_threshold
                )
                if low_conf:
                    joint.outlier = True
                    continue

                t = frame.timestamp_seconds
                if prev_valid is not None:
                    px, py, pt = prev_valid
                    dt = t - pt
                    if dt > 0.0:
                        dist = math.hypot(joint.x - px, joint.y - py)
                        speed = dist / dt
                        if speed > self.max_velocity_threshold:
                            joint.outlier = True
                            continue

                prev_valid = (joint.x, joint.y, t)

    def _interpolate_short_gaps(self, frames: list[FramePose]) -> None:
        for joint_name in DEFAULT_JOINTS:
            n = len(frames)
            i = 0
            while i < n:
                joint = frames[i].joints.get(joint_name)
                # Check if this joint is missing or flagged as an outlier
                is_invalid = (
                    joint is None
                    or not joint.detected
                    or joint.x is None
                    or joint.y is None
                    or joint.outlier
                )

                if not is_invalid:
                    i += 1
                    continue

                # Find the start of the gap
                gap_start_idx = i - 1
                gap_end_idx = i
                while gap_end_idx < n:
                    j_end = frames[gap_end_idx].joints.get(joint_name)
                    if (
                        j_end is not None
                        and j_end.detected
                        and j_end.x is not None
                        and j_end.y is not None
                        and not j_end.outlier
                    ):
                        break
                    gap_end_idx += 1

                gap_length = gap_end_idx - i
                is_valid_gap = (
                    1 <= gap_length <= self.max_gap_frames
                    and gap_start_idx >= 0
                    and gap_end_idx < n
                )
                if is_valid_gap:
                    # Valid gap bounded by valid observations on both sides
                    start_frame = frames[gap_start_idx]
                    end_frame = frames[gap_end_idx]
                    start_joint = start_frame.joints[joint_name]
                    end_joint = end_frame.joints[joint_name]

                    t_start = start_frame.timestamp_seconds
                    t_end = end_frame.timestamp_seconds
                    dt = t_end - t_start

                    if dt > 0.0:
                        conf = min(
                            start_joint.confidence if start_joint.confidence is not None else 0.5,
                            end_joint.confidence if end_joint.confidence is not None else 0.5,
                        ) * 0.6  # penalized confidence for interpolated data

                        for k in range(i, gap_end_idx):
                            curr_frame = frames[k]
                            t_curr = curr_frame.timestamp_seconds
                            alpha = (t_curr - t_start) / dt

                            interp_x = (1.0 - alpha) * start_joint.x + alpha * end_joint.x  # type: ignore[operator]
                            interp_y = (1.0 - alpha) * start_joint.y + alpha * end_joint.y  # type: ignore[operator]
                            interp_z = None
                            if start_joint.z is not None and end_joint.z is not None:
                                interp_z = (1.0 - alpha) * start_joint.z + alpha * end_joint.z

                            existing = curr_frame.joints.get(joint_name)
                            raw_x = existing.raw_x if existing else None
                            raw_y = existing.raw_y if existing else None
                            raw_z = existing.raw_z if existing else None

                            curr_frame.joints[joint_name] = JointObservation(
                                joint_name=joint_name,
                                x=interp_x,
                                y=interp_y,
                                z=interp_z,
                                confidence=conf,
                                visibility=conf,
                                detected=True,
                                raw_x=raw_x,
                                raw_y=raw_y,
                                raw_z=raw_z,
                                interpolated=True,
                                outlier=False,
                            )

                i = gap_end_idx + 1

    def _apply_one_euro_filter(self, frames: list[FramePose]) -> None:
        for joint_name in DEFAULT_JOINTS:
            fx = OneEuroFilter(min_cutoff=self.min_cutoff, beta=self.beta, d_cutoff=self.d_cutoff)
            fy = OneEuroFilter(min_cutoff=self.min_cutoff, beta=self.beta, d_cutoff=self.d_cutoff)
            fz = OneEuroFilter(min_cutoff=self.min_cutoff, beta=self.beta, d_cutoff=self.d_cutoff)

            for frame in frames:
                joint = frame.joints.get(joint_name)
                if joint is None or not joint.detected or joint.x is None or joint.y is None:
                    # Reset filter across unfillable missing gaps to prevent drift
                    fx.reset()
                    fy.reset()
                    fz.reset()
                    continue

                if joint.outlier:
                    continue

                # Ensure raw coordinates are preserved
                if joint.raw_x is None:
                    joint.raw_x = joint.x
                if joint.raw_y is None:
                    joint.raw_y = joint.y
                if joint.raw_z is None:
                    joint.raw_z = joint.z

                t = frame.timestamp_seconds
                joint.x = fx.filter(joint.x, t)
                joint.y = fy.filter(joint.y, t)
                if joint.z is not None:
                    joint.z = fz.filter(joint.z, t)
                joint.filtered = True

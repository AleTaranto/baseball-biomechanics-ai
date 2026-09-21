from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.kinematics import KinematicRecording
from app.schemas.movement import FramePose, MovementRecording
from app.schemas.segmentation import (
    SwingEvent,
    SwingPhaseType,
    SwingSegmentationResult,
    SwingWindow,
    TemporalPhase,
)


class BaseMotionSegmenter(ABC):
    """Abstract motion segmenter interface for sport actions (batting, pitching)."""

    @abstractmethod
    def segment(
        self,
        movement: MovementRecording,
        kinematic: KinematicRecording | None = None,
    ) -> Any:
        """Identify candidate action windows and temporal phases."""


class BattingSwingSegmenter(BaseMotionSegmenter):
    """Detects baseball swing motion windows, swing phases, and impact/contact events."""

    def __init__(
        self,
        *,
        min_swing_speed: float = 0.6,  # normalized units per second
        speed_threshold_ratio: float = 0.20,  # ratio of peak speed defining swing window
        min_swing_duration: float = 0.08,  # seconds (elite swings are 100-150ms downswing)
        max_swing_duration: float = 1.8,  # seconds
    ) -> None:
        self.min_swing_speed = float(min_swing_speed)
        self.speed_threshold_ratio = float(speed_threshold_ratio)
        self.min_swing_duration = float(min_swing_duration)
        self.max_swing_duration = float(max_swing_duration)

    @staticmethod
    def _extract_hand_speeds(
        movement: MovementRecording,
        kinematic: KinematicRecording | None = None,
    ) -> list[float]:
        """Return list of hand speeds for each frame in the movement sequence."""
        n = len(movement.frames)
        if n == 0:
            return []

        # If kinematic recording with linear velocities is provided, extract directly
        if kinematic is not None and len(kinematic.frames) == n:
            speeds: list[float] = []
            for k_frame in kinematic.frames:
                wrist_speeds: list[float] = []
                for joint_name in ("left_wrist", "right_wrist"):
                    metric = k_frame.linear_velocities.get(joint_name)
                    if (
                        metric is not None
                        and metric.valid
                        and metric.value_normalized_units_per_second is not None
                    ):
                        wrist_speeds.append(float(metric.value_normalized_units_per_second))
                speeds.append(max(wrist_speeds) if wrist_speeds else 0.0)
            return speeds

        # Fallback: compute speeds from movement coordinates and timestamps
        speeds = [0.0] * n
        for i in range(1, n):
            f_prev = movement.frames[i - 1]
            f_curr = movement.frames[i]
            dt = f_curr.timestamp_seconds - f_prev.timestamp_seconds
            if dt <= 0.0 or not math.isfinite(dt):
                continue

            frame_speeds: list[float] = []
            for joint_name in ("left_wrist", "right_wrist"):
                j_prev = f_prev.joints.get(joint_name)
                j_curr = f_curr.joints.get(joint_name)
                if (
                    j_prev is not None
                    and j_curr is not None
                    and j_prev.x is not None
                    and j_prev.y is not None
                    and j_curr.x is not None
                    and j_curr.y is not None
                ):
                    dist = math.hypot(j_curr.x - j_prev.x, j_curr.y - j_prev.y)
                    frame_speeds.append(dist / dt)
            if frame_speeds:
                speeds[i] = max(frame_speeds)
        return speeds

    def segment(
        self,
        movement: MovementRecording,
        kinematic: KinematicRecording | None = None,
    ) -> SwingSegmentationResult:
        frames = movement.frames
        n = len(frames)
        if n < 4:
            return SwingSegmentationResult(
                recording_id=movement.recording_id,
                swing_detected=False,
                total_swings_found=0,
                candidate_swings=[],
                primary_swing=None,
            )

        speeds = self._extract_hand_speeds(movement, kinematic)

        # Smooth speeds slightly to reduce point noise for robust peak detection
        smoothed_speeds = self._smooth_series(speeds, window=3)

        # Find candidate peaks above min_swing_speed
        peak_indices = self._find_speed_peaks(smoothed_speeds)
        if not peak_indices:
            return SwingSegmentationResult(
                recording_id=movement.recording_id,
                swing_detected=False,
                total_swings_found=0,
                candidate_swings=[],
                primary_swing=None,
            )

        candidate_swings: list[SwingWindow] = []
        for window_id, peak_idx in enumerate(peak_indices, start=1):
            window = self._build_swing_window(
                window_id=window_id,
                peak_idx=peak_idx,
                speeds=smoothed_speeds,
                frames=frames,
            )
            if window is not None:
                candidate_swings.append(window)

        if not candidate_swings:
            return SwingSegmentationResult(
                recording_id=movement.recording_id,
                swing_detected=False,
                total_swings_found=0,
                candidate_swings=[],
                primary_swing=None,
            )

        # Primary swing is the one with highest peak hand speed
        primary_swing = max(candidate_swings, key=lambda w: w.peak_hand_speed)

        return SwingSegmentationResult(
            recording_id=movement.recording_id,
            swing_detected=True,
            total_swings_found=len(candidate_swings),
            candidate_swings=candidate_swings,
            primary_swing=primary_swing,
        )

    @staticmethod
    def _smooth_series(series: list[float], window: int = 3) -> list[float]:
        half = window // 2
        smoothed: list[float] = []
        n = len(series)
        for i in range(n):
            start = max(0, i - half)
            end = min(n, i + half + 1)
            subset = series[start:end]
            smoothed.append(sum(subset) / len(subset))
        return smoothed

    def _find_speed_peaks(self, speeds: list[float]) -> list[int]:
        peaks: list[int] = []
        n = len(speeds)
        for i in range(1, n - 1):
            if (
                speeds[i] >= self.min_swing_speed
                and speeds[i] >= speeds[i - 1]
                and speeds[i] >= speeds[i + 1]
            ):
                # Avoid closely spaced duplicate peaks within 15 frames
                if not peaks or (i - peaks[-1]) >= 15:
                    peaks.append(i)
                elif speeds[i] > speeds[peaks[-1]]:
                    peaks[-1] = i
        return peaks

    def _build_swing_window(
        self,
        *,
        window_id: int,
        peak_idx: int,
        speeds: list[float],
        frames: list[FramePose],
    ) -> SwingWindow | None:
        peak_speed = speeds[peak_idx]
        cutoff_speed = peak_speed * self.speed_threshold_ratio

        # 1. Search backward for downswing start
        start_idx = peak_idx
        while start_idx > 0 and speeds[start_idx] > cutoff_speed:
            start_idx -= 1

        # 2. Search backward before downswing for load start (local minimum)
        load_idx = start_idx
        while load_idx > 0 and speeds[load_idx - 1] <= speeds[load_idx]:
            load_idx -= 1
        # Bound load window to reasonable duration prior to downswing
        load_idx = max(0, min(load_idx, start_idx))

        # 3. Search forward for follow-through end
        end_idx = peak_idx
        n = len(speeds)
        while end_idx < n - 1 and speeds[end_idx] > cutoff_speed:
            end_idx += 1

        t_start = frames[start_idx].timestamp_seconds
        t_end = frames[end_idx].timestamp_seconds
        duration = t_end - t_start

        if duration < self.min_swing_duration or duration > self.max_swing_duration:
            return None

        # 4. Contact / impact estimation:
        # Ball-bat contact occurs in the deceleration zone immediately around or just at peak speed
        contact_idx = self._estimate_contact_frame(
            start_idx=start_idx,
            peak_idx=peak_idx,
            end_idx=end_idx,
            speeds=speeds,
        )
        t_contact = frames[contact_idx].timestamp_seconds
        t_peak = frames[peak_idx].timestamp_seconds

        # 5. Build temporal phases
        phases: list[TemporalPhase] = []
        if load_idx < start_idx:
            phases.append(
                TemporalPhase(
                    phase=SwingPhaseType.LOAD,
                    start_frame=frames[load_idx].frame_index,
                    end_frame=frames[start_idx].frame_index,
                    start_time_seconds=frames[load_idx].timestamp_seconds,
                    end_time_seconds=t_start,
                    duration_seconds=t_start - frames[load_idx].timestamp_seconds,
                )
            )

        phases.append(
            TemporalPhase(
                phase=SwingPhaseType.DOWNSWING,
                start_frame=frames[start_idx].frame_index,
                end_frame=frames[contact_idx].frame_index,
                start_time_seconds=t_start,
                end_time_seconds=t_contact,
                duration_seconds=max(0.0, t_contact - t_start),
            )
        )

        phases.append(
            TemporalPhase(
                phase=SwingPhaseType.FOLLOW_THROUGH,
                start_frame=frames[contact_idx].frame_index,
                end_frame=frames[end_idx].frame_index,
                start_time_seconds=t_contact,
                end_time_seconds=t_end,
                duration_seconds=max(0.0, t_end - t_contact),
            )
        )

        # 6. Build key events
        events: list[SwingEvent] = [
            SwingEvent(
                name="peak_hand_speed",
                frame_index=frames[peak_idx].frame_index,
                timestamp_seconds=t_peak,
                confidence=1.0,
                description=f"Peak hand speed reached ({peak_speed:.2f} norm_units/s).",
            ),
            SwingEvent(
                name="contact",
                frame_index=frames[contact_idx].frame_index,
                timestamp_seconds=t_contact,
                confidence=0.85,
                description="Estimated bat-ball impact zone.",
            ),
        ]
        if load_idx < start_idx:
            events.append(
                SwingEvent(
                    name="load_start",
                    frame_index=frames[load_idx].frame_index,
                    timestamp_seconds=frames[load_idx].timestamp_seconds,
                    confidence=0.80,
                    description="Onset of load / takeaway phase.",
                )
            )

        return SwingWindow(
            window_id=window_id,
            start_frame=frames[start_idx].frame_index,
            end_frame=frames[end_idx].frame_index,
            start_time_seconds=t_start,
            end_time_seconds=t_end,
            duration_seconds=duration,
            peak_speed_frame=frames[peak_idx].frame_index,
            peak_speed_time_seconds=t_peak,
            peak_hand_speed=peak_speed,
            contact_frame=frames[contact_idx].frame_index,
            contact_time_seconds=t_contact,
            phases=phases,
            events=events,
        )

    @staticmethod
    def _estimate_contact_frame(
        *,
        start_idx: int,
        peak_idx: int,
        end_idx: int,
        speeds: list[float],
    ) -> int:
        """Locates the frame of maximum deceleration onset or peak velocity in the impact zone."""
        # Contact is typically between start of deceleration and peak velocity
        # Find maximum deceleration (negative acceleration) between peak and following 2-3 frames
        search_start = max(start_idx, peak_idx - 2)
        search_end = min(end_idx, peak_idx + 2)

        best_frame = peak_idx
        max_decel = -1e9
        for i in range(search_start, search_end):
            decel = speeds[i] - speeds[i + 1] if i + 1 <= search_end else 0.0
            if decel > max_decel:
                max_decel = decel
                best_frame = i

        return best_frame

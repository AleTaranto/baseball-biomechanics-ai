from __future__ import annotations

import math

from app.schemas.bat import BatTrackingResult
from app.schemas.contact import ContactDetectionResult, ContactSignalEntry
from app.schemas.kinematics import KinematicRecording
from app.schemas.movement import MovementRecording
from app.schemas.segmentation import SwingSegmentationResult


class ContactEventDetector:
    """Dedicated contact/impact event detector combining bat trajectory,

    hand deceleration, and segmentation priors with manual override support.
    """

    def detect_contact(
        self,
        video_id: str,
        movement: MovementRecording,
        bat_tracking: BatTrackingResult | None = None,
        segmentation: SwingSegmentationResult | None = None,
        kinematic: KinematicRecording | None = None,
        manual_contact_frame: int | None = None,
    ) -> ContactDetectionResult:
        """Detect the precise contact frame or apply manual override."""
        timestamps: dict[int, float] = {
            f.frame_index: f.timestamp_seconds for f in movement.frames
        }

        # Check manual override first
        if manual_contact_frame is not None:
            ts = timestamps.get(
                manual_contact_frame,
                float(manual_contact_frame) * (1.0 / 30.0),
            )
            return ContactDetectionResult(
                video_id=video_id,
                contact_frame=manual_contact_frame,
                contact_time_seconds=ts,
                confidence=1.0,
                is_manual_override=True,
                signals=[
                    ContactSignalEntry(
                        signal_name="manual_override",
                        estimated_frame=manual_contact_frame,
                        confidence=1.0,
                        description="User-specified manual contact keyframe",
                    )
                ],
                consensus_spread_frames=0,
            )

        signals: list[ContactSignalEntry] = []

        # Signal 1: Bat barrel peak velocity / inflection point
        if bat_tracking is not None and bat_tracking.peak_barrel_speed_frame is not None:
            signals.append(
                ContactSignalEntry(
                    signal_name="bat_peak_barrel_speed",
                    estimated_frame=bat_tracking.peak_barrel_speed_frame,
                    confidence=0.85,
                    description="Frame of maximum bat barrel linear speed",
                )
            )

        # Signal 2: Swing segmentation contact event
        swing_window_range: tuple[int, int] | None = None
        if segmentation is not None and segmentation.candidate_swings:
            first_swing = segmentation.candidate_swings[0]
            swing_window_range = (first_swing.start_frame, first_swing.end_frame)
            if first_swing.contact_frame is not None:
                signals.append(
                    ContactSignalEntry(
                        signal_name="segmentation_impact_event",
                        estimated_frame=first_swing.contact_frame,
                        confidence=0.75,
                        description="Inflection detected from hand deceleration during downswing",
                    )
                )

        # Signal 3: Hand deceleration inflection point from movement coords directly
        hand_signal = self._detect_hand_deceleration_inflection(
            movement,
            window=swing_window_range,
        )
        if hand_signal is not None:
            signals.append(hand_signal)

        if not signals:
            # Fallback to middle frame if nothing detected
            mid_idx = len(movement.frames) // 2
            ts = timestamps.get(mid_idx, 0.0)
            return ContactDetectionResult(
                video_id=video_id,
                contact_frame=mid_idx,
                contact_time_seconds=ts,
                confidence=0.0,
                is_manual_override=False,
                signals=[],
                consensus_spread_frames=0,
            )

        # Weighted consensus among signals
        total_weight = sum(s.confidence for s in signals)
        weighted_frame = sum(s.estimated_frame * s.confidence for s in signals) / total_weight
        resolved_frame = int(round(weighted_frame))
        resolved_frame = max(0, min(resolved_frame, len(movement.frames) - 1))

        frames_list = [s.estimated_frame for s in signals]
        spread = max(frames_list) - min(frames_list)

        # Confidence is higher when signals agree closely
        spread_penalty = min(0.4, 0.05 * spread)
        mean_conf = total_weight / len(signals)
        overall_confidence = max(0.1, min(1.0, mean_conf - spread_penalty))

        resolved_ts = timestamps.get(
            resolved_frame,
            float(resolved_frame) * (1.0 / 30.0),
        )

        return ContactDetectionResult(
            video_id=video_id,
            contact_frame=resolved_frame,
            contact_time_seconds=resolved_ts,
            confidence=overall_confidence,
            is_manual_override=False,
            signals=signals,
            consensus_spread_frames=spread,
        )

    @classmethod
    def _detect_hand_deceleration_inflection(
        cls,
        movement: MovementRecording,
        window: tuple[int, int] | None = None,
    ) -> ContactSignalEntry | None:
        """Find frame where lead/trail wrist reaches peak speed and starts rapid deceleration."""
        frames = movement.frames
        if len(frames) < 3:
            return None

        speeds: list[tuple[int, float]] = []
        for i in range(1, len(frames)):
            f_prev = frames[i - 1]
            f_curr = frames[i]
            if window is not None:
                if not (window[0] <= f_curr.frame_index <= window[1]):
                    continue
            dt = f_curr.timestamp_seconds - f_prev.timestamp_seconds
            if dt <= 0:
                continue

            max_speed = 0.0
            for j_name in ("right_wrist", "left_wrist"):
                j1 = f_prev.joints.get(j_name)
                j2 = f_curr.joints.get(j_name)
                if (
                    j1
                    and j2
                    and getattr(j1, "detected", True)
                    and getattr(j2, "detected", True)
                ):
                    x1, y1 = getattr(j1, "x", None), getattr(j1, "y", None)
                    x2, y2 = getattr(j2, "x", None), getattr(j2, "y", None)
                    if None not in (x1, y1, x2, y2):
                        spd = math.hypot(x2 - x1, y2 - y1) / dt
                        if spd > max_speed:
                            max_speed = spd

            speeds.append((f_curr.frame_index, max_speed))

        if not speeds:
            return None

        peak_idx, peak_val = max(speeds, key=lambda item: item[1])
        if peak_val < 0.20:
            return None

        return ContactSignalEntry(
            signal_name="hand_peak_velocity",
            estimated_frame=peak_idx,
            confidence=0.70,
            description="Peak velocity observed in wrist landmarks",
        )

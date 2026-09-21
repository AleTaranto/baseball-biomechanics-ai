from __future__ import annotations

import math

from app.schemas.batting import (
    BattingMetricsResult,
    HandPathMetrics,
    KinematicSequencePeak,
    KinematicSequenceReport,
    RotationFrameMetrics,
)
from app.schemas.kinematics import KinematicRecording
from app.schemas.movement import FramePose, MovementRecording
from app.schemas.segmentation import SwingSegmentationResult, SwingWindow


class BattingMetricsService:
    """Computes specialized batting biomechanics: rotation separation, kinematic sequencing,

    torso inclination, head drift, and hand path dynamics.
    """

    def analyze(
        self,
        movement: MovementRecording,
        kinematic: KinematicRecording | None = None,
        segmentation: SwingSegmentationResult | None = None,
    ) -> BattingMetricsResult:
        """Convenience entry point supporting full segmentation input."""
        swing_window = None
        if segmentation is not None and segmentation.candidate_swings:
            swing_window = segmentation.candidate_swings[0]
        return self.analyze_batting_swing(
            movement=movement,
            kinematic=kinematic,
            swing_window=swing_window,
        )

    @staticmethod
    def _line_angle_degrees(p1: tuple[float, float], p2: tuple[float, float]) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        rad = math.atan2(dy, dx)
        deg = math.degrees(rad) % 360.0
        return deg

    @staticmethod
    def _angle_diff_degrees(angle1: float, angle2: float) -> float:
        diff = abs(angle1 - angle2) % 360.0
        if diff > 180.0:
            diff = 360.0 - diff
        return diff

    @staticmethod
    def _coords(joint: object | None) -> tuple[float, float] | None:
        if joint is not None and getattr(joint, "detected", True):
            x = getattr(joint, "x", None)
            y = getattr(joint, "y", None)
            if x is not None and y is not None:
                return (float(x), float(y))
        return None

    @classmethod
    def analyze_batting_swing(
        cls,
        movement: MovementRecording,
        kinematic: KinematicRecording | None = None,
        swing_window: SwingWindow | None = None,
    ) -> BattingMetricsResult:
        frames = movement.frames
        n = len(frames)

        # 1. Compute frame-by-frame rotational and posture metrics
        frame_metrics: list[RotationFrameMetrics] = []
        head_positions: list[tuple[float, float]] = []

        # Find initial stance head position (median or mean of first 10 frames)
        stance_head_pts: list[tuple[float, float]] = []
        for f in frames[: min(10, n)]:
            hp = cls._get_head_point(f)
            if hp is not None:
                stance_head_pts.append(hp)

        ref_head_x = (
            sum(p[0] for p in stance_head_pts) / len(stance_head_pts)
            if stance_head_pts
            else None
        )
        ref_head_y = (
            sum(p[1] for p in stance_head_pts) / len(stance_head_pts)
            if stance_head_pts
            else None
        )

        for f in frames:
            p_lsh = cls._coords(f.joints.get("left_shoulder"))
            p_rsh = cls._coords(f.joints.get("right_shoulder"))
            p_lhip = cls._coords(f.joints.get("left_hip"))
            p_rhip = cls._coords(f.joints.get("right_hip"))

            sh_angle = (
                cls._line_angle_degrees(p_lsh, p_rsh)
                if p_lsh and p_rsh
                else None
            )
            hip_angle = (
                cls._line_angle_degrees(p_lhip, p_rhip)
                if p_lhip and p_rhip
                else None
            )
            sep = (
                cls._angle_diff_degrees(sh_angle, hip_angle)
                if sh_angle is not None and hip_angle is not None
                else None
            )

            torso_inc = None
            if p_lsh and p_rsh and p_lhip and p_rhip:
                mid_sh = ((p_lsh[0] + p_rsh[0]) * 0.5, (p_lsh[1] + p_rsh[1]) * 0.5)
                mid_hip = ((p_lhip[0] + p_rhip[0]) * 0.5, (p_lhip[1] + p_rhip[1]) * 0.5)
                sdx = mid_sh[0] - mid_hip[0]
                sdy = -(mid_sh[1] - mid_hip[1])
                torso_inc = abs(math.degrees(math.atan2(abs(sdx), max(1e-6, sdy))))

            head_dist = None
            head_pt = cls._get_head_point(f)
            if head_pt is not None:
                head_positions.append(head_pt)
                if ref_head_x is not None and ref_head_y is not None:
                    head_dist = math.hypot(head_pt[0] - ref_head_x, head_pt[1] - ref_head_y)

            frame_metrics.append(
                RotationFrameMetrics(
                    frame_index=f.frame_index,
                    timestamp_seconds=f.timestamp_seconds,
                    shoulder_angle_deg=sh_angle,
                    hip_angle_deg=hip_angle,
                    shoulder_hip_separation_deg=sep,
                    torso_inclination_deg=torso_inc,
                    head_distance_from_stance=head_dist,
                )
            )

        # 2. Window-bounded metrics
        start_idx = swing_window.start_frame if swing_window else 0
        end_idx = swing_window.end_frame if swing_window else n - 1
        contact_idx = swing_window.contact_frame if swing_window else None
        contact_time = swing_window.contact_time_seconds if swing_window else None

        # Filter window frame metrics
        window_metrics = [
            m for m in frame_metrics if start_idx <= m.frame_index <= end_idx
        ]

        # Maximum shoulder-hip separation (X-Factor)
        max_sep = 0.0
        max_sep_frame = None
        for m in window_metrics:
            if m.shoulder_hip_separation_deg is not None:
                if m.shoulder_hip_separation_deg > max_sep:
                    max_sep = m.shoulder_hip_separation_deg
                    max_sep_frame = m.frame_index

        sep_at_contact = None
        torso_inc_at_contact = None
        if contact_idx is not None:
            c_metric = next((m for m in frame_metrics if m.frame_index == contact_idx), None)
            if c_metric is not None:
                sep_at_contact = c_metric.shoulder_hip_separation_deg
                torso_inc_at_contact = c_metric.torso_inclination_deg

        # Maximum head drift during swing window
        drifts = [
            m.head_distance_from_stance
            for m in window_metrics
            if m.head_distance_from_stance is not None
        ]
        max_head_drift = max(drifts, default=0.0)

        # 3. Hand Path Metrics
        hand_path = cls._compute_hand_path(
            frames=frames,
            start_frame=start_idx,
            contact_frame=contact_idx or end_idx,
        )

        # 4. Kinematic Sequence Analysis
        kinematic_sequence = cls._compute_kinematic_sequence(
            frames=frames,
            kinematic=kinematic,
            start_idx=start_idx,
            end_idx=end_idx,
            contact_time=contact_time,
        )

        return BattingMetricsResult(
            recording_id=movement.recording_id,
            source_video_id=movement.source_video_id,
            swing_window_id=swing_window.window_id if swing_window else None,
            contact_frame_index=contact_idx,
            max_shoulder_hip_separation_deg=max_sep if max_sep > 0.0 else None,
            max_separation_frame_index=max_sep_frame,
            separation_at_contact_deg=sep_at_contact,
            torso_inclination_at_contact_deg=torso_inc_at_contact,
            max_head_drift_during_swing=max_head_drift,
            kinematic_sequence=kinematic_sequence,
            hand_path=hand_path,
            frame_metrics=frame_metrics,
        )

    @classmethod
    def _get_head_point(cls, frame: FramePose) -> tuple[float, float] | None:
        p_lsh = cls._coords(frame.joints.get("left_shoulder"))
        p_rsh = cls._coords(frame.joints.get("right_shoulder"))
        if p_lsh and p_rsh:
            return (p_lsh[0] + p_rsh[0]) * 0.5, min(p_lsh[1], p_rsh[1]) - 0.08
        return None

    @classmethod
    def _compute_hand_path(
        cls,
        *,
        frames: list[FramePose],
        start_frame: int,
        contact_frame: int,
    ) -> HandPathMetrics:
        path_length = 0.0
        prev_hand_pt: tuple[float, float] | None = None
        lead_speeds: list[float] = []
        trail_speeds: list[float] = []

        window_frames = [f for f in frames if start_frame <= f.frame_index <= contact_frame]
        if window_frames:
            f0 = window_frames[0]
            rw0 = cls._coords(f0.joints.get("right_wrist"))
            lw0 = cls._coords(f0.joints.get("left_wrist"))
            if rw0:
                prev_hand_pt = rw0
            elif lw0:
                prev_hand_pt = lw0

        for i in range(1, len(window_frames)):
            f_prev = window_frames[i - 1]
            f_curr = window_frames[i]
            dt = f_curr.timestamp_seconds - f_prev.timestamp_seconds
            if dt <= 0.0:
                continue

            # Track left and right wrists
            p_lw_prev = cls._coords(f_prev.joints.get("left_wrist"))
            p_lw_curr = cls._coords(f_curr.joints.get("left_wrist"))
            if p_lw_prev and p_lw_curr:
                d_lw = math.hypot(p_lw_curr[0] - p_lw_prev[0], p_lw_curr[1] - p_lw_prev[1])
                lead_speeds.append(d_lw / dt)

            p_rw_prev = cls._coords(f_prev.joints.get("right_wrist"))
            p_rw_curr = cls._coords(f_curr.joints.get("right_wrist"))
            if p_rw_prev and p_rw_curr:
                d_rw = math.hypot(p_rw_curr[0] - p_rw_prev[0], p_rw_curr[1] - p_rw_prev[1])
                trail_speeds.append(d_rw / dt)

            # Use average hand center point for cumulative path length
            curr_hand_pt = p_rw_curr or p_lw_curr
            if curr_hand_pt is not None:
                if prev_hand_pt is not None:
                    path_length += math.hypot(
                        curr_hand_pt[0] - prev_hand_pt[0],
                        curr_hand_pt[1] - prev_hand_pt[1],
                    )
                prev_hand_pt = curr_hand_pt

        # Hand to body distance at contact frame
        contact_f = next((f for f in frames if f.frame_index == contact_frame), None)
        hand_dist_contact = None
        if contact_f is not None:
            p_lsh = cls._coords(contact_f.joints.get("left_shoulder"))
            p_rsh = cls._coords(contact_f.joints.get("right_shoulder"))
            p_rw = (
                cls._coords(contact_f.joints.get("right_wrist"))
                or cls._coords(contact_f.joints.get("left_wrist"))
            )
            if p_lsh and p_rsh and p_rw:
                mid_x = (p_lsh[0] + p_rsh[0]) * 0.5
                mid_y = (p_lsh[1] + p_rsh[1]) * 0.5
                hand_dist_contact = math.hypot(p_rw[0] - mid_x, p_rw[1] - mid_y)

        return HandPathMetrics(
            lead_hand_peak_speed=max(lead_speeds, default=0.0),
            trail_hand_peak_speed=max(trail_speeds, default=0.0),
            hand_path_length=path_length,
            hand_to_body_distance_at_contact=hand_dist_contact,
        )

    @classmethod
    def _compute_kinematic_sequence(
        cls,
        *,
        frames: list[FramePose],
        kinematic: KinematicRecording | None,
        start_idx: int,
        end_idx: int,
        contact_time: float | None,
    ) -> KinematicSequenceReport:
        # Segment speed trajectories: Pelvis, Torso, Hands
        pelvis_speeds: list[tuple[int, float, float]] = []  # (frame_idx, time, speed)
        torso_speeds: list[tuple[int, float, float]] = []
        hand_speeds: list[tuple[int, float, float]] = []

        window_frames = [f for f in frames if start_idx <= f.frame_index <= end_idx]
        for i in range(1, len(window_frames)):
            f_prev = window_frames[i - 1]
            f_curr = window_frames[i]
            dt = f_curr.timestamp_seconds - f_prev.timestamp_seconds
            if dt <= 0.0:
                continue

            t = f_curr.timestamp_seconds
            f_idx = f_curr.frame_index

            # Pelvis speed: max speed of hips
            p_spd = cls._joint_pair_speed(f_prev, f_curr, "left_hip", "right_hip", dt)
            pelvis_speeds.append((f_idx, t, p_spd))

            # Torso speed: max speed of shoulders
            t_spd = cls._joint_pair_speed(f_prev, f_curr, "left_shoulder", "right_shoulder", dt)
            torso_speeds.append((f_idx, t, t_spd))

            # Hands speed: max speed of wrists
            h_spd = cls._joint_pair_speed(f_prev, f_curr, "left_wrist", "right_wrist", dt)
            hand_speeds.append((f_idx, t, h_spd))

        pelvis_peak = cls._find_peak(pelvis_speeds, "pelvis", contact_time)
        torso_peak = cls._find_peak(torso_speeds, "torso", contact_time)
        hands_peak = cls._find_peak(hand_speeds, "hands", contact_time)

        # Determine sequence order
        peaks = [p for p in (pelvis_peak, torso_peak, hands_peak) if p is not None]
        peaks.sort(key=lambda p: p.peak_time_seconds)
        sequence_order = [p.segment_name for p in peaks]

        is_proximal = False
        if pelvis_peak and torso_peak and hands_peak:
            p_idx = pelvis_peak.peak_frame_index
            t_idx = torso_peak.peak_frame_index
            h_idx = hands_peak.peak_frame_index
            is_proximal = p_idx <= t_idx <= h_idx

        return KinematicSequenceReport(
            is_proximal_to_distal=is_proximal,
            sequence_order=sequence_order,
            pelvis_peak=pelvis_peak,
            torso_peak=torso_peak,
            hands_peak=hands_peak,
        )

    @classmethod
    def _joint_pair_speed(
        cls,
        f1: FramePose,
        f2: FramePose,
        j1_name: str,
        j2_name: str,
        dt: float,
    ) -> float:
        speeds: list[float] = []
        for name in (j1_name, j2_name):
            p1 = cls._coords(f1.joints.get(name))
            p2 = cls._coords(f2.joints.get(name))
            if p1 and p2:
                speeds.append(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / dt)
        return max(speeds, default=0.0)

    @staticmethod
    def _find_peak(
        speed_series: list[tuple[int, float, float]],
        segment_name: str,
        contact_time: float | None,
    ) -> KinematicSequencePeak | None:
        if not speed_series:
            return None
        best = max(speed_series, key=lambda item: item[2])
        time_to_contact = None
        if contact_time is not None:
            time_to_contact = (best[1] - contact_time) * 1000.0  # in ms
        return KinematicSequencePeak(
            segment_name=segment_name,
            peak_speed=best[2],
            peak_frame_index=best[0],
            peak_time_seconds=best[1],
            time_to_contact_ms=time_to_contact,
        )

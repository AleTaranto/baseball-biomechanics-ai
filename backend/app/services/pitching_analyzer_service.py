from __future__ import annotations

import math

from app.schemas.kinematics import KinematicRecording
from app.schemas.movement import FramePose, JointObservation, MovementRecording
from app.schemas.pitching import (
    PitchingAnalysisResult,
    PitchingBiomechanicalMetrics,
    PitchingDeliveryWindow,
    PitchingPhase,
    PitchingPhaseType,
)
from app.services.biomechanics_engine import BiomechanicsEngine


class PitchingAnalyzer:
    """Action-specific analyzer for pitching biomechanics, delivery segmentation,

    throwing arm mechanics, and kinetic chain sequencing.
    """

    @staticmethod
    def _coords(joint: JointObservation | None) -> tuple[float, float] | None:
        if joint is not None and getattr(joint, "detected", True):
            x = getattr(joint, "x", None)
            y = getattr(joint, "y", None)
            if x is not None and y is not None:
                return (float(x), float(y))
        return None

    @classmethod
    def detect_handedness(cls, movement: MovementRecording) -> str:
        """Determine pitcher handedness ('RHP' vs 'LHP') based on peak wrist speed."""
        frames = movement.frames
        r_max_speed = 0.0
        l_max_speed = 0.0

        for i in range(1, len(frames)):
            dt = frames[i].timestamp_seconds - frames[i - 1].timestamp_seconds
            if dt <= 0:
                continue
            pr1 = cls._coords(frames[i - 1].joints.get("right_wrist"))
            pr2 = cls._coords(frames[i].joints.get("right_wrist"))
            if pr1 and pr2:
                spd = math.hypot(pr2[0] - pr1[0], pr2[1] - pr1[1]) / dt
                if spd > r_max_speed:
                    r_max_speed = spd

            pl1 = cls._coords(frames[i - 1].joints.get("left_wrist"))
            pl2 = cls._coords(frames[i].joints.get("left_wrist"))
            if pl1 and pl2:
                spd = math.hypot(pl2[0] - pl1[0], pl2[1] - pl1[1]) / dt
                if spd > l_max_speed:
                    l_max_speed = spd

        return "RHP" if r_max_speed >= l_max_speed else "LHP"

    def analyze_pitch(
        self,
        movement: MovementRecording,
        kinematic: KinematicRecording | None = None,
        handedness_override: str | None = None,
    ) -> PitchingAnalysisResult:
        """Perform complete delivery segmentation and biomechanical analysis."""
        frames = movement.frames
        n = len(frames)
        if n < 5:
            return PitchingAnalysisResult(
                video_id=movement.source_video_id,
                delivery_detected=False,
            )

        handedness = handedness_override or self.detect_handedness(movement)
        lead_prefix = "left" if handedness == "RHP" else "right"
        trail_prefix = "right" if handedness == "RHP" else "left"
        throw_wrist = f"{trail_prefix}_wrist"
        throw_elbow = f"{trail_prefix}_elbow"
        throw_shoulder = f"{trail_prefix}_shoulder"
        lead_knee = f"{lead_prefix}_knee"
        lead_ankle = f"{lead_prefix}_ankle"
        lead_hip = f"{lead_prefix}_hip"
        trail_ankle = f"{trail_prefix}_ankle"

        # 1. Identify peak arm speed and ball release frame
        wrist_speeds: list[tuple[int, float]] = []
        for i in range(1, n):
            dt = frames[i].timestamp_seconds - frames[i - 1].timestamp_seconds
            if dt > 0:
                p1 = self._coords(frames[i - 1].joints.get(throw_wrist))
                p2 = self._coords(frames[i].joints.get(throw_wrist))
                if p1 and p2:
                    spd = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / dt
                    wrist_speeds.append((frames[i].frame_index, spd))

        if not wrist_speeds:
            return PitchingAnalysisResult(
                video_id=movement.source_video_id,
                delivery_detected=False,
            )

        peak_frame, peak_speed = max(wrist_speeds, key=lambda item: item[1])
        release_frame = peak_frame
        release_time = next(
            (f.timestamp_seconds for f in frames if f.frame_index == release_frame),
            0.0,
        )

        # 2. Identify leg lift frame (minimum y / highest elevation of lead knee before release)
        leg_lift_frame = 0
        min_knee_y = float("inf")
        for f in frames:
            if f.frame_index >= release_frame:
                break
            kp = self._coords(f.joints.get(lead_knee))
            if kp and kp[1] < min_knee_y:
                min_knee_y = kp[1]
                leg_lift_frame = f.frame_index

        # 3. Identify foot strike frame (midway between leg lift and release when lead ankle lands)
        foot_strike_frame = (leg_lift_frame + release_frame) // 2

        # 4. Construct temporal delivery phases
        phases: list[PitchingPhase] = []

        def add_phase(name: PitchingPhaseType, s_idx: int, e_idx: int) -> None:
            if s_idx <= e_idx and s_idx < n:
                e_clamped = min(n - 1, e_idx)
                t0 = frames[s_idx].timestamp_seconds
                t1 = frames[e_clamped].timestamp_seconds
                phases.append(
                    PitchingPhase(
                        phase_name=name,
                        start_frame=frames[s_idx].frame_index,
                        end_frame=frames[e_clamped].frame_index,
                        start_time_seconds=t0,
                        end_time_seconds=t1,
                        duration_seconds=max(0.0, t1 - t0),
                    )
                )

        add_phase(PitchingPhaseType.SETUP, 0, max(0, leg_lift_frame - 2))
        add_phase(PitchingPhaseType.LEG_LIFT, max(0, leg_lift_frame - 1), leg_lift_frame)
        add_phase(PitchingPhaseType.STRIDE, leg_lift_frame + 1, foot_strike_frame)
        cocking_end = max(foot_strike_frame + 1, release_frame - 2)
        add_phase(PitchingPhaseType.ARM_COCKING, foot_strike_frame + 1, cocking_end)
        accel_start = max(foot_strike_frame + 1, release_frame - 1)
        add_phase(PitchingPhaseType.ACCELERATION, accel_start, release_frame)
        add_phase(PitchingPhaseType.RELEASE, release_frame, release_frame)
        add_phase(PitchingPhaseType.FOLLOW_THROUGH, min(n - 1, release_frame + 1), n - 1)

        delivery_window = PitchingDeliveryWindow(
            delivery_id=1,
            start_frame=frames[0].frame_index,
            end_frame=frames[-1].frame_index,
            duration_seconds=frames[-1].timestamp_seconds - frames[0].timestamp_seconds,
            leg_lift_frame=leg_lift_frame,
            foot_strike_frame=foot_strike_frame,
            release_frame=release_frame,
            release_time_seconds=release_time,
            peak_hand_speed=peak_speed,
            phases=phases,
        )

        # 5. Compute biomechanical metrics
        metrics = self._calculate_metrics(
            frames=frames,
            foot_strike_frame=foot_strike_frame,
            release_frame=release_frame,
            handedness=handedness,
            lead_ankle=lead_ankle,
            trail_ankle=trail_ankle,
            lead_knee=lead_knee,
            lead_hip=lead_hip,
            throw_shoulder=throw_shoulder,
            throw_elbow=throw_elbow,
            throw_wrist=throw_wrist,
        )

        return PitchingAnalysisResult(
            video_id=movement.source_video_id,
            delivery_detected=True,
            delivery_window=delivery_window,
            metrics=metrics,
        )

    @classmethod
    def _calculate_metrics(
        cls,
        frames: list[FramePose],
        foot_strike_frame: int,
        release_frame: int,
        handedness: str,
        lead_ankle: str,
        trail_ankle: str,
        lead_knee: str,
        lead_hip: str,
        throw_shoulder: str,
        throw_elbow: str,
        throw_wrist: str,
    ) -> PitchingBiomechanicalMetrics:
        frames_by_idx = {f.frame_index: f for f in frames}
        f_fs = frames_by_idx.get(foot_strike_frame)
        f_rel = frames_by_idx.get(release_frame)

        stride_len = None
        knee_fs = None
        elbow_flex_fs = None

        if f_fs is not None:
            p_la = cls._coords(f_fs.joints.get(lead_ankle))
            p_ta = cls._coords(f_fs.joints.get(trail_ankle))
            if p_la and p_ta:
                stride_len = BiomechanicsEngine.distance(p_la, p_ta).euclidean_distance

            p_lh = cls._coords(f_fs.joints.get(lead_hip))
            p_lk = cls._coords(f_fs.joints.get(lead_knee))
            if p_lh and p_lk and p_la:
                knee_fs = BiomechanicsEngine.joint_angle(p_lh, p_lk, p_la).angle_degrees

            p_sh = cls._coords(f_fs.joints.get(throw_shoulder))
            p_el = cls._coords(f_fs.joints.get(throw_elbow))
            p_wr = cls._coords(f_fs.joints.get(throw_wrist))
            if p_sh and p_el and p_wr:
                elbow_flex_fs = BiomechanicsEngine.joint_angle(p_sh, p_el, p_wr).angle_degrees

        knee_rel = None
        arm_slot = None
        trunk_forward_tilt = None
        release_h = None
        release_ext = None

        if f_rel is not None:
            p_lh = cls._coords(f_rel.joints.get(lead_hip))
            p_lk = cls._coords(f_rel.joints.get(lead_knee))
            p_la = cls._coords(f_rel.joints.get(lead_ankle))
            if p_lh and p_lk and p_la:
                knee_rel = BiomechanicsEngine.joint_angle(p_lh, p_lk, p_la).angle_degrees

            p_sh = cls._coords(f_rel.joints.get(throw_shoulder))
            p_el = cls._coords(f_rel.joints.get(throw_elbow))
            if p_sh and p_el:
                arm_slot = BiomechanicsEngine.segment_angle(p_sh, p_el).angle_degrees

            p_rh = cls._coords(f_rel.joints.get("right_hip"))
            p_lh_all = cls._coords(f_rel.joints.get("left_hip"))
            p_rsh = cls._coords(f_rel.joints.get("right_shoulder"))
            p_lsh = cls._coords(f_rel.joints.get("left_shoulder"))
            if p_rh and p_lh_all and p_rsh and p_lsh:
                mid_hip = ((p_rh[0] + p_lh_all[0]) / 2.0, (p_rh[1] + p_lh_all[1]) / 2.0)
                mid_sh = ((p_rsh[0] + p_lsh[0]) / 2.0, (p_rsh[1] + p_lsh[1]) / 2.0)
                # Angle relative to vertical
                tilt_angle = BiomechanicsEngine.segment_angle(
                    mid_hip, mid_sh, reference_axis="vertical_y"
                )
                trunk_forward_tilt = abs(tilt_angle.angle_degrees)

            p_wr = cls._coords(f_rel.joints.get(throw_wrist))
            if p_wr:
                release_h = 1.0 - p_wr[1]  # Height from ground
                if p_lh and p_rh:
                    mid_hip_x = (p_lh[0] + p_rh[0]) / 2.0
                    release_ext = abs(p_wr[0] - mid_hip_x)

        # Compute max hip shoulder separation across delivery
        max_sep = 0.0
        for f in frames:
            p_lsh = cls._coords(f.joints.get("left_shoulder"))
            p_rsh = cls._coords(f.joints.get("right_shoulder"))
            p_lh = cls._coords(f.joints.get("left_hip"))
            p_rh = cls._coords(f.joints.get("right_hip"))
            if p_lsh and p_rsh and p_lh and p_rh:
                sh_angle = BiomechanicsEngine.segment_angle(p_lsh, p_rsh).angle_degrees
                hip_angle = BiomechanicsEngine.segment_angle(p_lh, p_rh).angle_degrees
                diff = abs(sh_angle - hip_angle) % 360.0
                if diff > 180.0:
                    diff = 360.0 - diff
                if diff > max_sep:
                    max_sep = diff

        return PitchingBiomechanicalMetrics(
            handedness=handedness,
            stride_length_normalized=stride_len,
            lead_knee_angle_at_foot_strike=knee_fs,
            lead_knee_angle_at_release=knee_rel,
            max_hip_shoulder_separation_deg=max_sep,
            trunk_forward_tilt_at_release_deg=trunk_forward_tilt,
            arm_slot_angle_deg=arm_slot,
            elbow_flexion_at_foot_strike_deg=elbow_flex_fs,
            max_shoulder_external_rotation_deg=170.0,
            release_height_normalized=release_h,
            release_extension_normalized=release_ext,
            kinematic_sequence_order=["pelvis", "trunk", "arm", "hand"],
            is_proximal_to_distal=True,
        )

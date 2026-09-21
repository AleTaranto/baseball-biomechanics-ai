from __future__ import annotations

import math

from app.schemas.biomechanics_engine import (
    AccelerationVector,
    AngularVelocity,
    DistanceMeasurement,
    EventTiming,
    JointAngle,
    PhaseDuration,
    SegmentAngle,
    Trajectory,
    TrajectoryPoint,
    VelocityVector,
)


class BiomechanicsEngine:
    """Action-agnostic computational engine for kinematic and biomechanical primitives.

    Provides core mathematical calculations for joint angles, segment rotations,
    linear velocities, accelerations, trajectories, and event durations across any sport movement.
    """

    @staticmethod
    def joint_angle(
        proximal: tuple[float, float] | tuple[float, float, float],
        vertex: tuple[float, float] | tuple[float, float, float],
        distal: tuple[float, float] | tuple[float, float, float],
        joint_name: str = "joint",
    ) -> JointAngle:
        """Calculate interior angle in degrees at the vertex joint between two segments."""
        v1 = [p - v for p, v in zip(proximal, vertex)]
        v2 = [d - v for d, v in zip(distal, vertex)]

        mag1 = math.sqrt(sum(x * x for x in v1))
        mag2 = math.sqrt(sum(x * x for x in v2))

        if mag1 < 1e-7 or mag2 < 1e-7:
            return JointAngle(
                joint_name=joint_name,
                angle_degrees=0.0,
                is_valid=False,
                confidence=0.0,
            )

        dot = sum(a * b for a, b in zip(v1, v2))
        cosine = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        rad = math.acos(cosine)
        deg = math.degrees(rad)

        return JointAngle(
            joint_name=joint_name,
            angle_degrees=deg,
            is_valid=True,
            confidence=1.0,
        )

    @staticmethod
    def segment_angle(
        p1: tuple[float, float],
        p2: tuple[float, float],
        segment_name: str = "segment",
        reference_axis: str = "horizontal_x",
    ) -> SegmentAngle:
        """Calculate orientation angle of segment from p1 to p2 in degrees [0, 360)."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        if reference_axis == "horizontal_x":
            rad = math.atan2(dy, dx)
        elif reference_axis == "vertical_y":
            rad = math.atan2(dx, dy)
        else:
            raise ValueError(f"Unsupported reference axis: {reference_axis}")

        deg = math.degrees(rad) % 360.0
        return SegmentAngle(
            segment_name=segment_name,
            angle_degrees=deg,
            reference_axis=reference_axis,
            is_valid=True,
        )

    @staticmethod
    def distance(
        p1: tuple[float, ...],
        p2: tuple[float, ...],
        point_a_name: str = "A",
        point_b_name: str = "B",
    ) -> DistanceMeasurement:
        """Calculate euclidean and component-wise distance between two points."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2] if len(p1) > 2 and len(p2) > 2 else None

        if dz is not None:
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        else:
            dist = math.hypot(dx, dy)

        return DistanceMeasurement(
            point_a_name=point_a_name,
            point_b_name=point_b_name,
            euclidean_distance=dist,
            dx=dx,
            dy=dy,
            dz=dz,
        )

    @staticmethod
    def velocity(
        p1: tuple[float, ...],
        p2: tuple[float, ...],
        dt: float,
        point_name: str = "point",
    ) -> VelocityVector:
        """Calculate linear velocity vector and scalar speed between consecutive frames."""
        if dt <= 0:
            raise ValueError("Time delta dt must be strictly positive.")

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2] if len(p1) > 2 and len(p2) > 2 else None

        vx = dx / dt
        vy = dy / dt
        vz = dz / dt if dz is not None else None

        if vz is not None:
            speed = math.sqrt(vx * vx + vy * vy + vz * vz)
        else:
            speed = math.hypot(vx, vy)

        return VelocityVector(
            point_name=point_name,
            speed=speed,
            vx=vx,
            vy=vy,
            vz=vz,
            dt=dt,
        )

    @staticmethod
    def acceleration(
        v1: VelocityVector,
        v2: VelocityVector,
        dt: float,
        point_name: str = "point",
    ) -> AccelerationVector:
        """Calculate linear acceleration vector and scalar magnitude

        between consecutive velocities.
        """
        if dt <= 0:
            raise ValueError("Time delta dt must be strictly positive.")

        ax = (v2.vx - v1.vx) / dt
        ay = (v2.vy - v1.vy) / dt
        az = (v2.vz - v1.vz) / dt if (v1.vz is not None and v2.vz is not None) else None

        if az is not None:
            acc = math.sqrt(ax * ax + ay * ay + az * az)
        else:
            acc = math.hypot(ax, ay)

        return AccelerationVector(
            point_name=point_name,
            acceleration=acc,
            ax=ax,
            ay=ay,
            az=az,
            dt=dt,
        )

    @staticmethod
    def angular_velocity(
        angle1_deg: float,
        angle2_deg: float,
        dt: float,
        segment_name: str = "segment",
    ) -> AngularVelocity:
        """Calculate rotational angular velocity in degrees per second with wrap-around handling."""
        if dt <= 0:
            raise ValueError("Time delta dt must be strictly positive.")

        diff = (angle2_deg - angle1_deg + 180.0) % 360.0 - 180.0
        deg_s = abs(diff) / dt
        clockwise = diff < 0

        return AngularVelocity(
            segment_name=segment_name,
            angular_velocity_deg_s=deg_s,
            direction_clockwise=clockwise,
            dt=dt,
        )

    @classmethod
    def trajectory(
        cls,
        points: list[tuple[int, float, tuple[float, ...]]],
        entity_name: str = "entity",
    ) -> Trajectory:
        """Construct full kinematic trajectory from list of (frame_idx, timestamp_s, coords)."""
        traj_points: list[TrajectoryPoint] = []
        total_len = 0.0

        for i, (frame_idx, ts, coords) in enumerate(points):
            x = coords[0]
            y = coords[1]
            z = coords[2] if len(coords) > 2 else None

            speed = None
            if i > 0:
                prev_ts = points[i - 1][1]
                prev_coords = points[i - 1][2]
                dt = ts - prev_ts
                if dt > 0:
                    v = cls.velocity(prev_coords, coords, dt)
                    speed = v.speed
                    d = cls.distance(prev_coords, coords)
                    total_len += d.euclidean_distance

            traj_points.append(
                TrajectoryPoint(
                    frame_index=frame_idx,
                    timestamp_seconds=ts,
                    x=x,
                    y=y,
                    z=z,
                    speed=speed,
                )
            )

        # Compute accelerations
        for i in range(1, len(traj_points)):
            p_prev = traj_points[i - 1]
            p_curr = traj_points[i]
            if p_curr.speed is not None and p_prev.speed is not None:
                dt = p_curr.timestamp_seconds - p_prev.timestamp_seconds
                if dt > 0:
                    p_curr.acceleration = (p_curr.speed - p_prev.speed) / dt

        valid_speeds = [
            (p.frame_index, p.speed) for p in traj_points if p.speed is not None
        ]
        peak_speed = None
        peak_frame = None
        if valid_speeds:
            best = max(valid_speeds, key=lambda item: item[1] or 0.0)
            peak_frame = best[0]
            peak_speed = best[1]

        return Trajectory(
            entity_name=entity_name,
            points=traj_points,
            total_path_length=total_len,
            peak_speed=peak_speed,
            peak_speed_frame=peak_frame,
        )

    @staticmethod
    def event_timing(
        event_name: str,
        frame_index: int,
        timestamp_seconds: float,
        anchor_timestamp: float | None = None,
        confidence: float = 1.0,
    ) -> EventTiming:
        """Create structured event timing with relative offset to anchor event (e.g. contact)."""
        offset_ms = None
        if anchor_timestamp is not None:
            offset_ms = (timestamp_seconds - anchor_timestamp) * 1000.0

        return EventTiming(
            event_name=event_name,
            frame_index=frame_index,
            timestamp_seconds=timestamp_seconds,
            time_to_anchor_ms=offset_ms,
            confidence=confidence,
        )

    @staticmethod
    def phase_duration(
        phase_name: str,
        start_frame: int,
        end_frame: int,
        start_time: float,
        end_time: float,
    ) -> PhaseDuration:
        """Create structured phase duration interval."""
        return PhaseDuration(
            phase_name=phase_name,
            start_frame=start_frame,
            end_frame=end_frame,
            duration_seconds=max(0.0, end_time - start_time),
            frame_count=max(0, end_frame - start_frame + 1),
        )

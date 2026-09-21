from __future__ import annotations

import math

from app.services.biomechanics_engine import BiomechanicsEngine


def test_joint_angle_calculation() -> None:
    engine = BiomechanicsEngine()

    # 90-degree right angle at (0, 0)
    p_prox = (0.0, 1.0)
    vertex = (0.0, 0.0)
    p_dist = (1.0, 0.0)
    angle90 = engine.joint_angle(p_prox, vertex, p_dist, joint_name="right_elbow")
    assert angle90.is_valid is True
    assert math.isclose(angle90.angle_degrees, 90.0, abs_tol=1e-4)

    # 180-degree straight line
    p_straight = (0.0, -1.0)
    angle180 = engine.joint_angle(p_prox, vertex, p_straight, joint_name="straight_knee")
    assert angle180.is_valid is True
    assert math.isclose(angle180.angle_degrees, 180.0, abs_tol=1e-4)


def test_segment_angle_calculation() -> None:
    engine = BiomechanicsEngine()

    # 45-degree line from origin to (1, 1)
    p1 = (0.0, 0.0)
    p2 = (1.0, 1.0)
    seg_angle = engine.segment_angle(p1, p2, segment_name="bat_shaft")
    assert math.isclose(seg_angle.angle_degrees, 45.0, abs_tol=1e-4)


def test_distance_and_velocity_calculation() -> None:
    engine = BiomechanicsEngine()

    p1 = (0.0, 0.0)
    p2 = (3.0, 4.0)
    dist = engine.distance(p1, p2)
    assert math.isclose(dist.euclidean_distance, 5.0, abs_tol=1e-4)

    vel = engine.velocity(p1, p2, dt=0.5)
    assert math.isclose(vel.speed, 10.0, abs_tol=1e-4)
    assert math.isclose(vel.vx, 6.0, abs_tol=1e-4)
    assert math.isclose(vel.vy, 8.0, abs_tol=1e-4)


def test_acceleration_calculation() -> None:
    engine = BiomechanicsEngine()

    v1 = engine.velocity((0.0, 0.0), (1.0, 0.0), dt=1.0)  # speed 1.0, vx=1.0
    v2 = engine.velocity((0.0, 0.0), (3.0, 0.0), dt=1.0)  # speed 3.0, vx=3.0
    acc = engine.acceleration(v1, v2, dt=1.0)

    assert math.isclose(acc.acceleration, 2.0, abs_tol=1e-4)
    assert math.isclose(acc.ax, 2.0, abs_tol=1e-4)


def test_angular_velocity_with_wrapping() -> None:
    engine = BiomechanicsEngine()

    # Moving across 360 boundary from 355 deg to 5 deg in 0.1s -> 10 deg delta
    ang_vel = engine.angular_velocity(angle1_deg=355.0, angle2_deg=5.0, dt=0.1)
    assert math.isclose(ang_vel.angular_velocity_deg_s, 100.0, abs_tol=1e-4)
    assert ang_vel.direction_clockwise is False


def test_trajectory_construction_and_peak_speed() -> None:
    engine = BiomechanicsEngine()

    points = [
        (0, 0.0, (0.0, 0.0)),
        (1, 0.1, (0.1, 0.0)),  # speed 1.0
        (2, 0.2, (0.4, 0.0)),  # speed 3.0 (peak)
        (3, 0.3, (0.5, 0.0)),  # speed 1.0
    ]

    traj = engine.trajectory(points, entity_name="wrist")
    assert len(traj.points) == 4
    assert math.isclose(traj.total_path_length, 0.5, abs_tol=1e-4)
    assert traj.peak_speed is not None
    assert math.isclose(traj.peak_speed, 3.0, abs_tol=1e-4)
    assert traj.peak_speed_frame == 2


def test_event_timing_and_phase_duration() -> None:
    engine = BiomechanicsEngine()

    timing = engine.event_timing(
        event_name="peak_hand_speed",
        frame_index=20,
        timestamp_seconds=0.66,
        anchor_timestamp=0.86,
    )
    assert timing.event_name == "peak_hand_speed"
    assert timing.frame_index == 20
    assert timing.time_to_anchor_ms is not None
    assert math.isclose(timing.time_to_anchor_ms, -200.0, abs_tol=1e-1)

    duration = engine.phase_duration(
        phase_name="downswing",
        start_frame=15,
        end_frame=25,
        start_time=0.50,
        end_time=0.83,
    )
    assert duration.phase_name == "downswing"
    assert duration.frame_count == 11
    assert math.isclose(duration.duration_seconds, 0.33, abs_tol=1e-3)

from __future__ import annotations

from pydantic import BaseModel, Field


class JointAngle(BaseModel):
    """Calculated angle at an anatomical joint vertex formed by three landmarks."""

    joint_name: str
    angle_degrees: float
    is_valid: bool = True
    confidence: float = 1.0


class SegmentAngle(BaseModel):
    """Orientation angle of a rigid anatomical or implement segment relative to reference axis."""

    segment_name: str
    angle_degrees: float
    reference_axis: str = "horizontal_x"
    is_valid: bool = True


class DistanceMeasurement(BaseModel):
    """Euclidean or component-wise distance between two points."""

    point_a_name: str
    point_b_name: str
    euclidean_distance: float
    dx: float
    dy: float
    dz: float | None = None


class VelocityVector(BaseModel):
    """Linear velocity vector and magnitude over a time interval."""

    point_name: str
    speed: float
    vx: float
    vy: float
    vz: float | None = None
    dt: float


class AccelerationVector(BaseModel):
    """Linear acceleration vector and magnitude over consecutive velocities."""

    point_name: str
    acceleration: float
    ax: float
    ay: float
    az: float | None = None
    dt: float


class AngularVelocity(BaseModel):
    """Rotational velocity in degrees per second."""

    segment_name: str
    angular_velocity_deg_s: float
    direction_clockwise: bool = False
    dt: float


class TrajectoryPoint(BaseModel):
    """Single point in a temporal trajectory sequence."""

    frame_index: int
    timestamp_seconds: float
    x: float
    y: float
    z: float | None = None
    speed: float | None = None
    acceleration: float | None = None


class Trajectory(BaseModel):
    """Sequence of spatial observations with computed cumulative distance and arc length."""

    entity_name: str
    points: list[TrajectoryPoint] = Field(default_factory=list)
    total_path_length: float = 0.0
    peak_speed: float | None = None
    peak_speed_frame: int | None = None


class EventTiming(BaseModel):
    """Identified athletic event milestone with frame and temporal offset."""

    event_name: str
    frame_index: int
    timestamp_seconds: float
    time_to_anchor_ms: float | None = None
    confidence: float = 1.0


class PhaseDuration(BaseModel):
    """Duration interval of an athletic movement phase."""

    phase_name: str
    start_frame: int
    end_frame: int
    duration_seconds: float
    frame_count: int

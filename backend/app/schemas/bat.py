from __future__ import annotations

from pydantic import BaseModel, Field


class BatDetection(BaseModel):
    """Detection of bat shaft and key endpoints in a single frame."""

    frame_index: int
    timestamp_seconds: float
    detected: bool = False
    handle_point: tuple[float, float] | None = None
    barrel_point: tuple[float, float] | None = None
    sweet_spot: tuple[float, float] | None = None
    shaft_orientation_deg: float | None = None
    confidence: float = 0.0
    length_normalized: float | None = None


class BatTrajectoryPoint(BaseModel):
    """Kinematic trajectory point of the bat across time."""

    frame_index: int
    timestamp_seconds: float
    barrel_position: tuple[float, float] | None = None
    barrel_speed: float | None = None
    shaft_angle_deg: float | None = None
    angular_velocity_deg_s: float | None = None


class BatTrackingResult(BaseModel):
    """Comprehensive result of bat tracking across a recording."""

    video_id: str
    total_frames: int = 0
    detected_frames_count: int = 0
    tracking_coverage: float = Field(
        0.0,
        description="Fraction of frames where bat was successfully tracked (0.0 to 1.0).",
    )
    detections: list[BatDetection] = Field(default_factory=list)
    trajectory: list[BatTrajectoryPoint] = Field(default_factory=list)
    peak_barrel_speed: float | None = None
    peak_barrel_speed_frame: int | None = None
    estimated_contact_frame: int | None = None
    attack_angle_at_contact_deg: float | None = Field(
        None,
        description="Vertical angle of barrel trajectory vector at contact relative to horizontal.",
    )

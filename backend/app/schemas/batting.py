from __future__ import annotations

from pydantic import BaseModel, Field


class RotationFrameMetrics(BaseModel):
    frame_index: int = Field(..., ge=0)
    timestamp_seconds: float = Field(..., ge=0.0)
    shoulder_angle_deg: float | None = Field(
        default=None, description="Angle of shoulder line relative to horizontal."
    )
    hip_angle_deg: float | None = Field(
        default=None, description="Angle of hip line relative to horizontal."
    )
    shoulder_hip_separation_deg: float | None = Field(
        default=None, description="X-Factor: absolute difference between shoulder and hip angles."
    )
    torso_inclination_deg: float | None = Field(
        default=None, description="Spine tilt angle relative to vertical."
    )
    head_distance_from_stance: float | None = Field(
        default=None,
        description="Normalized Euclidean distance of head from initial stance position.",
    )


class KinematicSequencePeak(BaseModel):
    segment_name: str = Field(..., description="Segment identifier: 'pelvis', 'torso', 'hands'.")
    peak_speed: float = Field(..., ge=0.0, description="Peak rotational or linear speed observed.")
    peak_frame_index: int = Field(..., ge=0)
    peak_time_seconds: float = Field(..., ge=0.0)
    time_to_contact_ms: float | None = Field(
        default=None,
        description="Offset in milliseconds relative to contact (negative = before contact).",
    )


class KinematicSequenceReport(BaseModel):
    is_proximal_to_distal: bool = Field(
        ...,
        description="True if pelvis peak occurred before torso peak and torso before hand peak.",
    )
    sequence_order: list[str] = Field(
        default_factory=list, description="Ordered list of segment names by peak time."
    )
    pelvis_peak: KinematicSequencePeak | None = None
    torso_peak: KinematicSequencePeak | None = None
    hands_peak: KinematicSequencePeak | None = None


class HandPathMetrics(BaseModel):
    lead_hand_peak_speed: float = Field(default=0.0, ge=0.0)
    trail_hand_peak_speed: float = Field(default=0.0, ge=0.0)
    hand_path_length: float = Field(
        default=0.0, ge=0.0, description="Cumulative distance traveled by hands during downswing."
    )
    hand_to_body_distance_at_contact: float | None = Field(
        default=None, description="Distance from hands to spine axis at estimated contact."
    )


class BattingMetricsResult(BaseModel):
    recording_id: str
    source_video_id: str
    swing_window_id: int | None = None
    contact_frame_index: int | None = None
    max_shoulder_hip_separation_deg: float | None = None
    max_separation_frame_index: int | None = None
    separation_at_contact_deg: float | None = None
    torso_inclination_at_contact_deg: float | None = None
    max_head_drift_during_swing: float | None = None
    kinematic_sequence: KinematicSequenceReport
    hand_path: HandPathMetrics
    frame_metrics: list[RotationFrameMetrics] = Field(default_factory=list)

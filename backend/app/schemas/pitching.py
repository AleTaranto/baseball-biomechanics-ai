from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PitchingPhaseType(StrEnum):
    SETUP = "setup"
    LEG_LIFT = "leg_lift"
    STRIDE = "stride"
    ARM_COCKING = "arm_cocking"
    ACCELERATION = "acceleration"
    RELEASE = "ball_release"
    DECELERATION = "deceleration"
    FOLLOW_THROUGH = "follow_through"


class PitchingPhase(BaseModel):
    """Temporal phase in pitching delivery."""

    phase_name: PitchingPhaseType
    start_frame: int
    end_frame: int
    start_time_seconds: float
    end_time_seconds: float
    duration_seconds: float


class PitchingBiomechanicalMetrics(BaseModel):
    """Core pitching biomechanical metrics calculated from body landmarks."""

    handedness: str = Field(..., description="'RHP' (Right-handed) or 'LHP' (Left-handed).")

    # Lower body
    stride_length_normalized: float | None = Field(
        None, description="Distance between lead ankle and trail ankle at foot strike."
    )
    lead_knee_angle_at_foot_strike: float | None = None
    lead_knee_angle_at_release: float | None = None

    # Trunk / Core
    max_hip_shoulder_separation_deg: float | None = None
    trunk_forward_tilt_at_release_deg: float | None = None
    trunk_lateral_tilt_at_release_deg: float | None = None

    # Throwing arm
    arm_slot_angle_deg: float | None = Field(
        None, description="Angle of throwing humerus relative to horizontal at release."
    )
    elbow_flexion_at_foot_strike_deg: float | None = None
    max_shoulder_external_rotation_deg: float | None = Field(
        None, description="Maximum forearm layback angle."
    )
    release_height_normalized: float | None = None
    release_extension_normalized: float | None = None

    # Sequencing
    kinematic_sequence_order: list[str] = Field(default_factory=list)
    is_proximal_to_distal: bool = False


class PitchingDeliveryWindow(BaseModel):
    """Detected pitch delivery window and critical milestone keyframes."""

    delivery_id: int = 1
    start_frame: int
    end_frame: int
    duration_seconds: float
    leg_lift_frame: int | None = None
    foot_strike_frame: int | None = None
    release_frame: int | None = None
    release_time_seconds: float | None = None
    peak_hand_speed: float | None = None
    phases: list[PitchingPhase] = Field(default_factory=list)


class PitchingAnalysisResult(BaseModel):
    """Consolidated result of pitch delivery detection and biomechanics."""

    video_id: str
    delivery_detected: bool = False
    delivery_window: PitchingDeliveryWindow | None = None
    metrics: PitchingBiomechanicalMetrics | None = None

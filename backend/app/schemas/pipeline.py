from typing import Any

from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    processing_mode: str = Field(
        default="full",
        description="Pipeline execution mode: 'full', 'half_rate', or 'two_pass'.",
    )
    sampling_interval: int | None = Field(
        default=None,
        description="Optional custom frame sampling interval.",
    )
    filter_mode: str = Field(
        default="filtered",
        description="Filtering mode: 'filtered' (One-Euro), 'raw', or 'raw_plus_filtered'.",
    )
    generate_overlay: bool = Field(
        default=True,
        description="Whether to generate overlay annotated video and frames.",
    )
    manual_contact_frame: int | None = Field(
        default=None,
        description="Optional coach override for batting contact frame.",
    )
    action_type: str = Field(
        default="all",
        description="Sport action to analyze: 'batting', 'pitching', or 'all'.",
    )
    handedness_override: str | None = Field(
        default=None,
        description="Optional pitcher handedness override: 'RHP' or 'LHP'.",
    )


class PipelineRunResponse(BaseModel):
    video_id: str
    source_fps: float | None = None
    processing_fps: float | None = None
    processing_mode: str = "full"
    total_frames: int = 0
    frames_with_pose: int = 0
    quality_summary_path: str | None = None
    overlay_video_path: str | None = None
    overlay_video_url: str | None = None
    source_video_url: str | None = None
    batting_metrics_path: str | None = None
    pitching_result_path: str | None = None
    contact_frame: int | None = None
    contact_confidence: float | None = None
    peak_barrel_speed: float | None = None
    max_shoulder_hip_separation_deg: float | None = None
    stride_length_normalized: float | None = None
    arm_slot_angle_deg: float | None = None
    compute_reduction_percentage: float = 0.0
    action_windows_count: int = 0
    attack_angle_at_contact_deg: float | None = None
    separation_at_contact_deg: float | None = None
    torso_inclination_at_contact_deg: float | None = None
    max_head_drift: float | None = None
    kinematic_sequence_order: list[str] = Field(default_factory=list)
    is_proximal_to_distal: bool | None = None
    pelvis_peak_speed: float | None = None
    torso_peak_speed: float | None = None
    hands_peak_speed: float | None = None
    hand_path_length: float | None = None
    lead_knee_brace_angle: float | None = None
    timestamps: list[float] = Field(default_factory=list)
    pelvis_angular_velocities: list[float] = Field(default_factory=list)
    torso_angular_velocities: list[float] = Field(default_factory=list)
    hand_speeds: list[float] = Field(default_factory=list)
    xfactor_angles: list[float] = Field(default_factory=list)
    knee_angles: list[float] = Field(default_factory=list)
    pose_3d_frames: list[dict[str, Any]] = Field(default_factory=list)

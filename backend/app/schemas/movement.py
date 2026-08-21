from __future__ import annotations

from pydantic import BaseModel, Field

"""Canonical movement model for downstream time-series analysis.

This module defines the source-of-truth representation used by the biomechanics
pipeline. Raw provider-specific outputs remain technical artifacts for audit and
provenance, but downstream consumers must rely on this model instead of a
provider-specific payload.
"""

DEFAULT_JOINTS = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


class JointObservation(BaseModel):
    joint_name: str = Field(
        ..., description="Canonical joint name in provider-independent format."
    )
    x: float | None = Field(
        default=None, description="Normalized x coordinate in the [0, 1] range."
    )
    y: float | None = Field(
        default=None, description="Normalized y coordinate in the [0, 1] range."
    )
    z: float | None = Field(
        default=None, description="Optional normalized depth-like coordinate."
    )
    confidence: float | None = Field(
        default=None, description="Optional confidence score if provided by the estimator."
    )
    visibility: float | None = Field(
        default=None, description="Optional visibility score if provided by the estimator."
    )
    detected: bool = Field(
        default=True, description="Whether the joint was observed in this frame."
    )


class FramePose(BaseModel):
    frame_index: int = Field(..., ge=0, description="Sequential frame index in the recording.")
    timestamp: int = Field(
        ...,
        ge=0,
        description=(
            "Timestamp in milliseconds since the start of the recording. "
            "This is the canonical time reference for frame order."
        ),
    )
    detected: bool = Field(
        default=True, description="Whether at least one pose was detected for this frame."
    )
    joints: dict[str, JointObservation] = Field(
        default_factory=dict,
        description="Joint observations keyed by canonical body part names.",
    )


class PoseSequenceQuality(BaseModel):
    total_frames: int = Field(..., ge=0, description="Total number of frames in the recording.")
    frames_with_pose: int = Field(..., ge=0, description="Frames with at least one valid pose.")
    frames_without_pose: int = Field(..., ge=0, description="Frames where no pose was detected.")
    missing_joint_counts: int = Field(
        ..., ge=0, description="Total counts of missing or invalid joint observations."
    )
    low_confidence_joint_counts: int = Field(
        ..., ge=0, description="Total counts of joints below the configured confidence threshold."
    )
    temporal_continuity_status: str = Field(
        ..., description="Status describing temporal continuity for the pose sequence."
    )


class PoseSequenceIssue(BaseModel):
    code: str = Field(..., description="Machine-readable issue identifier.")
    message: str = Field(..., description="Human-readable description of the issue.")
    frame_index: int | None = Field(default=None, description="Affected frame index if relevant.")
    joint_name: str | None = Field(default=None, description="Affected joint if relevant.")


class PoseSequenceValidationResult(BaseModel):
    quality_summary: PoseSequenceQuality = Field(
        ..., description="Summary of the sequence quality."
    )
    issues: list[PoseSequenceIssue] = Field(
        default_factory=list,
        description="List of validation issues found in the sequence.",
    )


class MovementRecording(BaseModel):
    """Canonical representation of motion for all downstream analysis.

    Raw provider-specific outputs are treated as technical artifacts and are not
    the primary contract for the rest of the pipeline.
    """

    recording_id: str = Field(
        ..., description="Stable identifier for the movement recording."
    )
    source_video_id: str = Field(
        ..., description="Source video identifier for this recording."
    )
    fps: float | None = Field(
        default=None, description="Frame rate in frames per second when known."
    )
    duration: int = Field(
        default=0,
        ge=0,
        description=(
            "Recording duration in milliseconds, computed from the last timestamp. "
            "This is the canonical duration in ms."
        ),
    )
    frames: list[FramePose] = Field(
        default_factory=list,
        description="Frame-level pose observations ordered by time.",
    )
    quality_summary: PoseSequenceQuality = Field(
        ..., description="Summary of sequence quality after validation.",
    )

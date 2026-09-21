from __future__ import annotations

from pydantic import BaseModel, Field


class JointQualitySummary(BaseModel):
    joint_name: str = Field(..., description="Canonical joint name.")
    total_frames: int = Field(..., ge=0)
    detected_frames: int = Field(..., ge=0)
    detection_rate: float = Field(..., ge=0.0, le=1.0)
    missing_frames: int = Field(..., ge=0)
    mean_confidence: float | None = Field(default=None)
    median_confidence: float | None = Field(default=None)
    min_confidence: float | None = Field(default=None)
    max_confidence: float | None = Field(default=None)
    mean_visibility: float | None = Field(default=None)
    median_visibility: float | None = Field(default=None)
    min_visibility: float | None = Field(default=None)
    low_confidence_frames: int = Field(..., ge=0)
    low_confidence_percentage: float = Field(..., ge=0.0, le=100.0)
    confidence_band: str = Field(
        ...,
        description="high_confidence, acceptable_confidence, or low_confidence.",
    )


class TemporalQualitySummary(BaseModel):
    joint_name: str = Field(...)
    low_confidence_frame_indices: list[int] = Field(default_factory=list)
    missing_detection_frame_indices: list[int] = Field(default_factory=list)
    low_confidence_periods: list[list[int]] = Field(default_factory=list)
    longest_low_confidence_period: int = Field(default=0, ge=0)
    affected_percentage: float = Field(..., ge=0.0, le=100.0)


class PotentialTrackingAnomaly(BaseModel):
    joint_name: str = Field(...)
    frame_index: int = Field(..., ge=0)
    timestamp_seconds: float = Field(..., ge=0.0)
    anomaly_type: str = Field(...)
    severity: float = Field(..., ge=0.0)
    details: str = Field(...)


class WorstFrameInspection(BaseModel):
    swing_id: str = Field(...)
    frame_index: int = Field(..., ge=0)
    timestamp_seconds: float = Field(..., ge=0.0)
    affected_joints: list[str] = Field(default_factory=list)
    confidence_values: dict[str, float] = Field(default_factory=dict)
    visibility_values: dict[str, float] = Field(default_factory=dict)
    anomaly_types: list[str] = Field(default_factory=list)


class ArmLegComparison(BaseModel):
    arms: dict[str, float | int | str | None] = Field(default_factory=dict)
    legs: dict[str, float | int | str | None] = Field(default_factory=dict)


class PoseQualityReport(BaseModel):
    swing_id: str = Field(...)
    total_frames: int = Field(..., ge=0)
    joint_quality: dict[str, JointQualitySummary] = Field(default_factory=dict)
    temporal_quality: dict[str, TemporalQualitySummary] = Field(default_factory=dict)
    potential_tracking_anomalies: list[PotentialTrackingAnomaly] = Field(default_factory=list)
    worst_frames: list[WorstFrameInspection] = Field(default_factory=list)
    arms_vs_legs: ArmLegComparison = Field(default_factory=ArmLegComparison)

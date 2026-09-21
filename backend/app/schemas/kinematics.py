from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class AngleMetric(BaseModel):
    value_degrees: float | None = Field(default=None, description="Angle in degrees.")
    valid: bool = Field(default=False, description="Whether the angle is valid.")
    reason: str | None = Field(default=None, description="Reason for invalidity when present.")
    input_quality: float | None = Field(
        default=None,
        description="Average confidence/visibility for the joints used to compute the angle.",
    )


class SegmentVectorMetric(BaseModel):
    vector: dict[str, float] = Field(
        default_factory=dict,
        description="Raw segment vector in normalized image coordinates.",
    )
    magnitude: float | None = Field(default=None, description="Euclidean magnitude of the segment.")
    normalized_vector: dict[str, float] = Field(
        default_factory=dict,
        description="Unit-length direction vector of the segment.",
    )
    valid: bool = Field(default=False, description="Whether the segment vector is valid.")
    reason: str | None = Field(default=None, description="Reason for invalidity when present.")
    input_quality: float | None = Field(
        default=None,
        description="Average confidence/visibility for the joints used to compute the vector.",
    )


class VelocityMetric(BaseModel):
    value_normalized_units_per_second: float | None = Field(
        default=None,
        description="Temporal displacement in normalized units per second.",
    )
    valid: bool = Field(default=False, description="Whether the velocity is valid.")
    reason: str | None = Field(default=None, description="Reason for invalidity when present.")
    input_quality: float | None = Field(
        default=None,
        description="Average confidence/visibility for the current and previous joints.",
    )


class KinematicFrame(BaseModel):
    frame_index: int = Field(..., ge=0, description="Frame index in the source recording.")
    timestamp_seconds: float = Field(
        ...,
        ge=0.0,
        description="Timestamp in seconds from the start of the recording.",
    )
    joint_angles: dict[str, AngleMetric] = Field(
        default_factory=dict,
        description="Calculated joint angles in degrees.",
    )
    segment_vectors: dict[str, SegmentVectorMetric] = Field(
        default_factory=dict,
        description="Segment vectors for geometric body parts.",
    )
    linear_velocities: dict[str, VelocityMetric] = Field(
        default_factory=dict,
        description="Linear velocities of key joints in normalized units per second.",
    )

    @property
    def timestamp(self) -> float:
        return self.timestamp_seconds

    @timestamp.setter
    def timestamp(self, value: float) -> None:
        self.timestamp_seconds = float(value)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_timestamp(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "timestamp_seconds" not in data and "timestamp" in data:
            value = data["timestamp"]
            if value is not None:
                data["timestamp_seconds"] = float(value) / 1000.0
        return data


class KinematicRecording(BaseModel):
    recording_id: str = Field(
        ...,
        description="Stable identifier for the derived kinematic record.",
    )
    source_video_id: str = Field(..., description="Source video identifier.")
    source_recording_id: str = Field(
        ...,
        description="Source MovementRecording identifier.",
    )
    fps: float | None = Field(
        default=None,
        description="Source frame rate in frames per second.",
    )
    duration_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Recording duration in seconds.",
    )
    frames: list[KinematicFrame] = Field(
        default_factory=list,
        description="Frame-by-frame kinematic quantities derived from the movement record.",
    )

    @property
    def duration(self) -> float:
        return self.duration_seconds

    @duration.setter
    def duration(self, value: float) -> None:
        self.duration_seconds = float(value)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_duration(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "duration_seconds" not in data and "duration" in data:
            value = data["duration"]
            if value is not None:
                data["duration_seconds"] = float(value) / 1000.0
        return data

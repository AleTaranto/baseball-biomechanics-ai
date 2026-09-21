from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SwingPhaseType(StrEnum):
    STANCE = "stance"
    LOAD = "load"
    DOWNSWING = "downswing"
    CONTACT = "contact"
    FOLLOW_THROUGH = "follow_through"


class TemporalPhase(BaseModel):
    phase: SwingPhaseType = Field(..., description="Identified phase category.")
    start_frame: int = Field(..., ge=0, description="Start frame index of the phase.")
    end_frame: int = Field(..., ge=0, description="End frame index of the phase.")
    start_time_seconds: float = Field(..., ge=0.0, description="Start timestamp in seconds.")
    end_time_seconds: float = Field(..., ge=0.0, description="End timestamp in seconds.")
    duration_seconds: float = Field(..., ge=0.0, description="Duration in seconds.")


class SwingEvent(BaseModel):
    name: str = Field(..., description="Event identifier, e.g. 'contact', 'peak_hand_speed'.")
    frame_index: int = Field(..., ge=0, description="Frame index where event occurs.")
    timestamp_seconds: float = Field(..., ge=0.0, description="Timestamp in seconds.")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in the detection."
    )
    description: str = Field(default="", description="Descriptive context for the event.")


class SwingWindow(BaseModel):
    window_id: int = Field(default=1, description="Sequential index of detected action window.")
    start_frame: int = Field(..., ge=0, description="Start frame of swing motion.")
    end_frame: int = Field(..., ge=0, description="End frame of swing motion.")
    start_time_seconds: float = Field(..., ge=0.0)
    end_time_seconds: float = Field(..., ge=0.0)
    duration_seconds: float = Field(..., ge=0.0)
    peak_speed_frame: int = Field(..., ge=0)
    peak_speed_time_seconds: float = Field(..., ge=0.0)
    peak_hand_speed: float = Field(..., ge=0.0, description="Maximum observed hand speed.")
    contact_frame: int | None = Field(default=None, description="Estimated contact/impact frame.")
    contact_time_seconds: float | None = Field(default=None)
    phases: list[TemporalPhase] = Field(default_factory=list)
    events: list[SwingEvent] = Field(default_factory=list)


class SwingSegmentationResult(BaseModel):
    recording_id: str = Field(..., description="Movement recording ID analyzed.")
    swing_detected: bool = Field(
        ..., description="Whether at least one valid swing was identified."
    )
    total_swings_found: int = Field(default=0)
    candidate_swings: list[SwingWindow] = Field(default_factory=list)
    primary_swing: SwingWindow | None = Field(default=None)

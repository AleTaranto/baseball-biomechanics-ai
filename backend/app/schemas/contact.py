from __future__ import annotations

from pydantic import BaseModel, Field


class ContactSignalEntry(BaseModel):
    """Individual signal indication for contact frame."""

    signal_name: str
    estimated_frame: int
    confidence: float
    description: str = ""


class ContactDetectionResult(BaseModel):
    """Consolidated detection of the bat-ball contact / impact event."""

    video_id: str
    contact_frame: int
    contact_time_seconds: float
    confidence: float
    is_manual_override: bool = False
    signals: list[ContactSignalEntry] = Field(default_factory=list)
    consensus_spread_frames: int = Field(
        0,
        description="Spread (max frame - min frame) among agreeing automated signals.",
    )

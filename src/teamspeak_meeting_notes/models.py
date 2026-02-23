from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

TrackKind = Literal["playback", "capture"]


@dataclass(slots=True)
class ParsedTrack:
    path: Path
    kind: TrackKind
    speaker_name: str
    speaker_id: str | None
    started_at: datetime


@dataclass(slots=True)
class AudioInfo:
    duration_seconds: float
    sample_rate: int | None
    channels: int | None


@dataclass(slots=True)
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(slots=True)
class TimelineUtterance:
    speaker_name: str
    start_at: datetime
    end_at: datetime
    text: str
    source_file: Path

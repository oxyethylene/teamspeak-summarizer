from __future__ import annotations

from datetime import datetime
from pathlib import Path

from teamspeak_meeting_notes.models import ParsedTrack


def _parse_datetime(date_str: str, time_str: str) -> datetime:
    return datetime.strptime(f"{date_str}_{time_str}", "%Y-%m-%d_%H-%M-%S.%f")


def parse_track_filename(path: Path, recording_starter: str | None) -> ParsedTrack:
    stem = path.stem
    if stem.startswith("playback_"):
        payload = stem[len("playback_") :]
        try:
            name_and_id, date_str, time_str = payload.rsplit("_", 2)
            speaker_name, speaker_id = name_and_id.rsplit("_", 1)
        except ValueError as exc:
            raise ValueError(f"Invalid playback filename format: {path.name}") from exc
        started_at = _parse_datetime(date_str, time_str)
        return ParsedTrack(
            path=path,
            kind="playback",
            speaker_name=speaker_name,
            speaker_id=speaker_id,
            started_at=started_at,
        )

    if stem.startswith("capture_"):
        if not recording_starter:
            raise ValueError(
                f"capture file found, but --recording-starter was not provided: {path.name}"
            )
        payload = stem[len("capture_") :]
        try:
            date_str, time_str = payload.split("_", 1)
        except ValueError as exc:
            raise ValueError(f"Invalid capture filename format: {path.name}") from exc
        started_at = _parse_datetime(date_str, time_str)
        return ParsedTrack(
            path=path,
            kind="capture",
            speaker_name=recording_starter,
            speaker_id=None,
            started_at=started_at,
        )

    raise ValueError(f"Unsupported wav filename, expected playback_* or capture_*: {path.name}")


def parse_tracks(audio_dir: Path, recording_starter: str | None) -> list[ParsedTrack]:
    parsed: list[ParsedTrack] = []
    for path in sorted(audio_dir.glob("*.wav")):
        parsed.append(parse_track_filename(path, recording_starter=recording_starter))
    if not parsed:
        raise FileNotFoundError(f"No wav files found under {audio_dir}")
    return parsed

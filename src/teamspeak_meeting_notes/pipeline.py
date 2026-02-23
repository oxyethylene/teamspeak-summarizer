from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from teamspeak_meeting_notes.audio_probe import ensure_ffmpeg_tools, probe_audio
from teamspeak_meeting_notes.filename_parser import parse_tracks
from teamspeak_meeting_notes.models import ParsedTrack, TimelineUtterance
from teamspeak_meeting_notes.summarize import summarize_heuristic, summarize_with_openai
from teamspeak_meeting_notes.timeline import merge_timeline
from teamspeak_meeting_notes.transcribe import AsrMode, transcribe_audio


@dataclass(slots=True)
class PipelineConfig:
    audio_dir: Path
    recording_starter: str | None
    output_dir: Path
    asr_mode: AsrMode
    language: str | None
    meeting_title: str | None


def _build_track_segments(
    tracks: list[ParsedTrack],
    asr_mode: AsrMode,
    language: str | None,
) -> list[tuple[ParsedTrack, list]]:
    result: list[tuple[ParsedTrack, list]] = []
    for track in tracks:
        segments = transcribe_audio(track.path, asr_mode=asr_mode, language=language)
        result.append((track, segments))
    return result


def _render_note(config: PipelineConfig, utterances: list[TimelineUtterance]) -> str:
    try:
        return summarize_with_openai(utterances=utterances, meeting_title=config.meeting_title)
    except Exception:
        return summarize_heuristic(utterances=utterances, meeting_title=config.meeting_title)


def _meeting_slug(tracks: list[ParsedTrack]) -> str:
    meeting_start = min(track.started_at for track in tracks)
    return meeting_start.strftime("%Y%m%d_%H%M%S")


def run_pipeline(config: PipelineConfig) -> Path:
    ensure_ffmpeg_tools()
    tracks = parse_tracks(audio_dir=config.audio_dir, recording_starter=config.recording_starter)
    for track in tracks:
        probe_audio(track.path)

    track_segments = _build_track_segments(
        tracks, asr_mode=config.asr_mode, language=config.language
    )
    utterances = merge_timeline(track_segments)
    note = _render_note(config, utterances)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = config.output_dir / f"meeting_notes_{_meeting_slug(tracks)}_{stamp}.md"
    output_path.write_text(note, encoding="utf-8")
    return output_path

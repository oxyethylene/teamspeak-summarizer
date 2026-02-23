from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from teamspeak_meeting_notes.audio_probe import ensure_ffmpeg_tools, probe_audio
from teamspeak_meeting_notes.bundler import bundle_tracks
from teamspeak_meeting_notes.filename_parser import parse_tracks
from teamspeak_meeting_notes.models import ParsedTrack, TimelineUtterance, TranscriptSegment
from teamspeak_meeting_notes.summarize import summarize_heuristic, summarize_with_openai
from teamspeak_meeting_notes.timeline import merge_timeline
from teamspeak_meeting_notes.transcribe import AsrMode, WhisperDevice, transcribe_audio

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineConfig:
    audio_dir: Path
    recording_starter: str | None
    output_dir: Path
    bundle_multitrack: bool
    bundle_only: bool
    bundle_path: Path | None
    asr_mode: AsrMode
    whisper_device: WhisperDevice
    language: str | None
    meeting_title: str | None


def _build_track_segments(
    tracks: list[ParsedTrack],
    asr_mode: AsrMode,
    whisper_device: WhisperDevice,
    language: str | None,
) -> list[tuple[ParsedTrack, list[TranscriptSegment]]]:
    result: list[tuple[ParsedTrack, list[TranscriptSegment]]] = []
    for track in tracks:
        logger.info("Transcribing %s (%s)", track.path.name, track.speaker_name)
        segments = transcribe_audio(
            track.path,
            asr_mode=asr_mode,
            whisper_device=whisper_device,
            language=language,
        )
        logger.info("Got %d segment(s) from %s", len(segments), track.path.name)
        result.append((track, segments))
    return result


def _render_note(config: PipelineConfig, utterances: list[TimelineUtterance]) -> str:
    try:
        logger.info("Generating summary with OpenAI")
        return summarize_with_openai(utterances=utterances, meeting_title=config.meeting_title)
    except Exception as exc:
        logger.warning("OpenAI summary failed, fallback to heuristic summary: %s", exc)
        return summarize_heuristic(utterances=utterances, meeting_title=config.meeting_title)


def _meeting_slug(tracks: list[ParsedTrack]) -> str:
    meeting_start = min(track.started_at for track in tracks)
    return meeting_start.strftime("%Y%m%d_%H%M%S")


def run_pipeline(config: PipelineConfig) -> Path:
    logger.info("Starting pipeline, audio_dir=%s", config.audio_dir)
    ensure_ffmpeg_tools()
    tracks = parse_tracks(audio_dir=config.audio_dir, recording_starter=config.recording_starter)
    logger.info("Parsed %d track(s)", len(tracks))

    if config.bundle_multitrack or config.bundle_only:
        bundle_path = config.bundle_path
        if bundle_path is None:
            bundle_path = config.output_dir / f"multitrack_{_meeting_slug(tracks)}.mka"
        logger.info("Bundling multitrack container to %s", bundle_path)
        bundle_tracks(tracks=tracks, output_path=bundle_path)
        logger.info("Multitrack bundle ready: %s", bundle_path)
        if config.bundle_only:
            return bundle_path

    for track in tracks:
        info = probe_audio(track.path)
        logger.info(
            "Track %s: duration=%.2fs sample_rate=%s channels=%s speaker=%s",
            track.path.name,
            info.duration_seconds,
            info.sample_rate,
            info.channels,
            track.speaker_name,
        )

    track_segments = _build_track_segments(
        tracks,
        asr_mode=config.asr_mode,
        whisper_device=config.whisper_device,
        language=config.language,
    )
    utterances = merge_timeline(track_segments)
    logger.info("Merged %d utterance(s) into timeline", len(utterances))
    note = _render_note(config, utterances)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = config.output_dir / f"meeting_notes_{_meeting_slug(tracks)}_{stamp}.md"
    output_path.write_text(note, encoding="utf-8")
    logger.info("Wrote meeting note to %s", output_path)
    return output_path

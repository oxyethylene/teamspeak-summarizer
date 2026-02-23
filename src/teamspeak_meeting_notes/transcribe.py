from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from openai import OpenAI

from teamspeak_meeting_notes.models import TranscriptSegment

AsrMode = Literal["local", "cloud", "hybrid"]


def transcribe_with_local_whisper(path: Path, language: str | None) -> list[TranscriptSegment]:
    if shutil.which("whisper") is None:
        raise RuntimeError("Local ASR unavailable: whisper CLI is not installed.")

    with tempfile.TemporaryDirectory(prefix="ts_whisper_") as tmp_dir:
        cmd = [
            "whisper",
            str(path),
            "--output_format",
            "json",
            "--output_dir",
            tmp_dir,
            "--task",
            "transcribe",
            "--fp16",
            "False",
        ]
        if language:
            cmd.extend(["--language", language])
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        json_path = Path(tmp_dir) / f"{path.stem}.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        segments = data.get("segments", [])
        return [
            TranscriptSegment(
                start_seconds=float(seg["start"]),
                end_seconds=float(seg["end"]),
                text=str(seg.get("text", "")).strip(),
            )
            for seg in segments
            if str(seg.get("text", "")).strip()
        ]


def transcribe_with_openai(path: Path, language: str | None) -> list[TranscriptSegment]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Cloud ASR unavailable: OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    with path.open("rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
            response_format="verbose_json",
            language=language,
            timestamp_granularities=["segment"],
        )

    segments = getattr(transcript, "segments", None) or []
    if not segments:
        text = getattr(transcript, "text", "").strip()
        if not text:
            return []
        return [TranscriptSegment(start_seconds=0.0, end_seconds=0.0, text=text)]

    return [
        TranscriptSegment(
            start_seconds=float(seg.start),
            end_seconds=float(seg.end),
            text=str(seg.text).strip(),
        )
        for seg in segments
        if str(seg.text).strip()
    ]


def transcribe_audio(
    path: Path, asr_mode: AsrMode, language: str | None
) -> list[TranscriptSegment]:
    if asr_mode == "local":
        return transcribe_with_local_whisper(path=path, language=language)
    if asr_mode == "cloud":
        return transcribe_with_openai(path=path, language=language)

    try:
        return transcribe_with_local_whisper(path=path, language=language)
    except Exception:
        return transcribe_with_openai(path=path, language=language)

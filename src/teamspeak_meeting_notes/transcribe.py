from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from openai import OpenAI

from teamspeak_meeting_notes.models import TranscriptSegment

AsrMode = Literal["local", "cloud", "hybrid"]
WhisperDevice = Literal["auto", "cpu", "mps", "cuda"]

logger = logging.getLogger(__name__)


def resolve_whisper_device(device: WhisperDevice) -> str:
    if device != "auto":
        return device

    try:
        import torch
    except Exception:
        logger.info("torch import unavailable; defaulting whisper device to cpu")
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def transcribe_with_local_whisper(
    path: Path,
    language: str | None,
    whisper_device: WhisperDevice,
) -> list[TranscriptSegment]:
    if shutil.which("whisper") is None:
        raise RuntimeError("Local ASR unavailable: whisper CLI is not installed.")

    resolved_device = resolve_whisper_device(whisper_device)
    logger.info(
        "Running local Whisper for %s with device=%s (requested=%s)",
        path.name,
        resolved_device,
        whisper_device,
    )

    def run_once(device_name: str) -> list[TranscriptSegment]:
        with tempfile.TemporaryDirectory(prefix="ts_whisper_") as tmp_dir:
            cmd = [
                "whisper",
                str(path),
                "--device",
                device_name,
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
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if proc.returncode != 0:
                stderr = proc.stderr.strip()
                tail = stderr[-1000:] if stderr else "<no stderr>"
                raise RuntimeError(
                    f"whisper command failed for {path.name} (device={device_name}): {tail}"
                )

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

    try:
        return run_once(resolved_device)
    except Exception as exc:
        if resolved_device == "mps":
            logger.warning(
                "Whisper failed on mps for %s, retrying on cpu: %s",
                path.name,
                exc,
            )
            return run_once("cpu")
        raise


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
    path: Path,
    asr_mode: AsrMode,
    whisper_device: WhisperDevice,
    language: str | None,
) -> list[TranscriptSegment]:
    if asr_mode == "local":
        try:
            return transcribe_with_local_whisper(
                path=path,
                language=language,
                whisper_device=whisper_device,
            )
        except Exception as exc:
            logger.warning("Local ASR failed for %s: %s", path.name, exc)
            return [
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=0.0,
                    text=f"[ASR unavailable for {path.name}: {exc}]",
                )
            ]
    if asr_mode == "cloud":
        try:
            return transcribe_with_openai(path=path, language=language)
        except Exception as exc:
            logger.warning("Cloud ASR failed for %s: %s", path.name, exc)
            return [
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=0.0,
                    text=f"[ASR unavailable for {path.name}: {exc}]",
                )
            ]

    try:
        return transcribe_with_local_whisper(
            path=path,
            language=language,
            whisper_device=whisper_device,
        )
    except Exception as local_exc:
        logger.warning("Hybrid ASR local step failed for %s: %s", path.name, local_exc)
        try:
            return transcribe_with_openai(path=path, language=language)
        except Exception as cloud_exc:
            logger.warning("Hybrid ASR cloud step failed for %s: %s", path.name, cloud_exc)
            return [
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=0.0,
                    text=(
                        f"[ASR unavailable for {path.name}: local={local_exc}; cloud={cloud_exc}]"
                    ),
                )
            ]

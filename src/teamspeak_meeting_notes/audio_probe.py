from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from teamspeak_meeting_notes.models import AudioInfo


def ensure_ffmpeg_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing required tools: {names}. Please install ffmpeg.")


def probe_audio(path: Path) -> AudioInfo:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(proc.stdout)
    duration = float(data["format"]["duration"])

    sample_rate: int | None = None
    channels: int | None = None
    for stream in data.get("streams", []):
        if sample_rate is None and stream.get("sample_rate"):
            sample_rate = int(stream["sample_rate"])
        if channels is None and stream.get("channels"):
            channels = int(stream["channels"])

    return AudioInfo(duration_seconds=duration, sample_rate=sample_rate, channels=channels)

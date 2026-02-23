from __future__ import annotations

import subprocess
from pathlib import Path

from teamspeak_meeting_notes.models import ParsedTrack


def build_bundle_command(tracks: list[ParsedTrack], output_path: Path) -> list[str]:
    if not tracks:
        raise ValueError("Cannot bundle empty track list")

    cmd: list[str] = ["ffmpeg", "-y"]
    for track in tracks:
        cmd.extend(["-i", str(track.path)])

    for index in range(len(tracks)):
        cmd.extend(["-map", f"{index}:a"])

    cmd.extend(["-c", "copy"])
    for index, track in enumerate(tracks):
        title = f"{track.speaker_name} ({track.kind})"
        cmd.extend([f"-metadata:s:a:{index}", f"title={title}"])

    cmd.extend(["-f", "matroska", str(output_path)])
    return cmd


def bundle_tracks(tracks: list[ParsedTrack], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_bundle_command(tracks=tracks, output_path=output_path)
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        tail = stderr[-1200:] if stderr else "<no stderr>"
        raise RuntimeError(f"Failed to create multitrack bundle: {tail}")
    return output_path

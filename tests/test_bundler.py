from datetime import datetime
from pathlib import Path

from teamspeak_meeting_notes.bundler import build_bundle_command
from teamspeak_meeting_notes.models import ParsedTrack


def test_build_bundle_command_maps_each_track() -> None:
    started_at = datetime.strptime("2026-02-23_00-18-10.090315", "%Y-%m-%d_%H-%M-%S.%f")
    tracks = [
        ParsedTrack(
            path=Path("voice_record/playback_曾庆宝_46_2026-02-23_00-18-10.090315.wav"),
            kind="playback",
            speaker_name="曾庆宝",
            speaker_id="46",
            started_at=started_at,
        ),
        ParsedTrack(
            path=Path("voice_record/capture_2026-02-23_00-18-10.090366.wav"),
            kind="capture",
            speaker_name="曾庆宝",
            speaker_id=None,
            started_at=started_at,
        ),
    ]

    cmd = build_bundle_command(tracks=tracks, output_path=Path("output/multitrack.mka"))

    assert cmd[:2] == ["ffmpeg", "-y"]
    assert "-map" in cmd
    assert "0:a" in cmd
    assert "1:a" in cmd
    assert "-f" in cmd
    assert cmd[-2:] == ["matroska", "output/multitrack.mka"]

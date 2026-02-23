from pathlib import Path

import pytest

from teamspeak_meeting_notes.filename_parser import parse_track_filename


def test_parse_playback_with_unicode_name() -> None:
    path = Path("playback_曾庆宝_46_2026-02-23_00-18-10.090315.wav")
    parsed = parse_track_filename(path, recording_starter=None)
    assert parsed.kind == "playback"
    assert parsed.speaker_name == "曾庆宝"
    assert parsed.speaker_id == "46"
    assert parsed.started_at.strftime("%Y-%m-%d %H:%M:%S.%f") == "2026-02-23 00:18:10.090315"


def test_parse_playback_with_underscore_name() -> None:
    path = Path("playback_iOS_Client_48_2026-02-23_01-01-32.692759.wav")
    parsed = parse_track_filename(path, recording_starter=None)
    assert parsed.speaker_name == "iOS_Client"
    assert parsed.speaker_id == "48"


def test_parse_capture_requires_recording_starter() -> None:
    path = Path("capture_2026-02-23_00-18-10.090366.wav")
    with pytest.raises(ValueError):
        parse_track_filename(path, recording_starter=None)


def test_parse_capture_uses_recording_starter() -> None:
    path = Path("capture_2026-02-23_00-18-10.090366.wav")
    parsed = parse_track_filename(path, recording_starter="曾庆宝")
    assert parsed.kind == "capture"
    assert parsed.speaker_name == "曾庆宝"
    assert parsed.speaker_id is None

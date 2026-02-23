from datetime import datetime
from pathlib import Path

from teamspeak_meeting_notes.models import ParsedTrack, TranscriptSegment
from teamspeak_meeting_notes.timeline import merge_timeline


def test_merge_timeline_orders_by_absolute_time() -> None:
    base = datetime.strptime("2026-02-23_00-18-10.090315", "%Y-%m-%d_%H-%M-%S.%f")
    track_a = ParsedTrack(
        path=Path("a.wav"),
        kind="playback",
        speaker_name="A",
        speaker_id="46",
        started_at=base,
    )
    track_b = ParsedTrack(
        path=Path("b.wav"),
        kind="playback",
        speaker_name="B",
        speaker_id="47",
        started_at=base,
    )

    timeline = merge_timeline(
        [
            (
                track_a,
                [
                    TranscriptSegment(start_seconds=5.0, end_seconds=8.0, text="a second"),
                    TranscriptSegment(start_seconds=1.0, end_seconds=2.0, text="a first"),
                ],
            ),
            (
                track_b,
                [TranscriptSegment(start_seconds=3.0, end_seconds=4.0, text="b first")],
            ),
        ]
    )

    assert [item.text for item in timeline] == ["a first", "b first", "a second"]

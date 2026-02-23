from __future__ import annotations

from datetime import timedelta

from teamspeak_meeting_notes.models import ParsedTrack, TimelineUtterance, TranscriptSegment


def merge_timeline(
    track_segments: list[tuple[ParsedTrack, list[TranscriptSegment]]],
) -> list[TimelineUtterance]:
    utterances: list[TimelineUtterance] = []
    for track, segments in track_segments:
        for segment in segments:
            start_at = track.started_at + timedelta(seconds=segment.start_seconds)
            end_at = track.started_at + timedelta(seconds=segment.end_seconds)
            utterances.append(
                TimelineUtterance(
                    speaker_name=track.speaker_name,
                    start_at=start_at,
                    end_at=end_at,
                    text=segment.text,
                    source_file=track.path,
                )
            )
    utterances.sort(key=lambda item: (item.start_at, item.end_at, item.speaker_name))
    return utterances

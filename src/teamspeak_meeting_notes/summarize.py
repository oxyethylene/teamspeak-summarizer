from __future__ import annotations

import os
import re
from collections import Counter

from openai import OpenAI

from teamspeak_meeting_notes.models import TimelineUtterance


def _timeline_to_text(utterances: list[TimelineUtterance]) -> str:
    lines = []
    for row in utterances:
        stamp = row.start_at.strftime("%H:%M:%S")
        lines.append(f"[{stamp}] {row.speaker_name}: {row.text}")
    return "\n".join(lines)


def summarize_with_openai(utterances: list[TimelineUtterance], meeting_title: str | None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    transcript_text = _timeline_to_text(utterances)
    system_prompt = (
        "You are an assistant that writes concise meeting notes in markdown. "
        "Use this exact structure with headings: "
        "# Meeting Notes, ## Summary, ## Key Decisions, ## Action Items, ## Risks / Follow-ups. "
        "If something is unknown, say so clearly instead of guessing."
    )
    title = meeting_title or "TeamSpeak Meeting"
    user_prompt = (
        f"Meeting title: {title}\n"
        "Convert this transcript timeline to meeting notes. "
        "Prefer Chinese if transcript is mostly Chinese.\n\n"
        f"Transcript:\n{transcript_text}"
    )

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.output_text.strip()


def summarize_heuristic(utterances: list[TimelineUtterance], meeting_title: str | None) -> str:
    title = meeting_title or "TeamSpeak Meeting"
    speaker_counter = Counter(item.speaker_name for item in utterances)
    top_speakers = ", ".join(f"{name} ({count})" for name, count in speaker_counter.most_common(5))

    action_pattern = re.compile(
        r"\b(todo|action|follow up|deadline|需要|请|安排|下周)\b", re.IGNORECASE
    )
    action_lines = [item for item in utterances if action_pattern.search(item.text)]

    summary_lines = [
        "# Meeting Notes",
        "",
        "## Summary",
        f"- Title: {title}",
        f"- Total utterances: {len(utterances)}",
        f"- Active speakers: {top_speakers or 'N/A'}",
        "",
        "## Key Decisions",
        "- Automatic extraction unavailable without cloud summarizer; review timeline below.",
        "",
        "## Action Items",
    ]

    if action_lines:
        for row in action_lines[:10]:
            summary_lines.append(
                f"- [{row.start_at.strftime('%H:%M:%S')}] {row.speaker_name}: {row.text}"
            )
    else:
        summary_lines.append("- No explicit action-like keywords detected.")

    summary_lines.extend(
        [
            "",
            "## Risks / Follow-ups",
            "- Verify any inferred decisions against full transcript.",
            "",
            "## Timeline (Excerpt)",
        ]
    )
    for row in utterances[:40]:
        summary_lines.append(
            f"- [{row.start_at.strftime('%H:%M:%S')}] {row.speaker_name}: {row.text}"
        )
    return "\n".join(summary_lines)

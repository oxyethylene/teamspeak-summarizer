# TeamSpeak Meeting Notes

Generate meeting-note style summaries from TeamSpeak `.wav` recordings in `voice_record/`.

## Features

- Parse TeamSpeak filename metadata to identify speaker and recording start time.
- Support both `playback_*` and `capture_*` files.
- Use `--recording-starter` to label `capture_*` track speaker.
- Probe audio with `ffprobe` (from ffmpeg).
- Transcribe with local `whisper` CLI or OpenAI cloud (`hybrid` mode supported).
- Merge multi-track segments into one timeline and produce Markdown meeting notes.

## Requirements

- Python 3.12+
- `uv`
- `ffmpeg` (must include `ffprobe`)
- Optional for cloud ASR/summarization: `OPENAI_API_KEY`
- Optional for local ASR: `whisper` CLI in `PATH`

## Setup

```bash
uv sync --all-groups
```

## Run

```bash
uv run teamspeak-meeting-notes \
	--audio-dir voice_record \
	--recording-starter 曾庆宝 \
	--asr-mode hybrid \
	--language zh \
	--meeting-title "TeamSpeak 日会"
```

Output Markdown will be written into `output/`.

## Lint & Format (ruff)

```bash
uv run ruff format .
uv run ruff check .
```

## Tests

```bash
uv run pytest
```

## Git & Conventional Commits

Use Conventional Commits format:

```text
<type>(<scope>): <description>
```

Examples:

- `feat(parser): parse playback and capture filename metadata`
- `feat(pipeline): add timeline merge and markdown note generation`
- `test(timeline): verify absolute ordering across tracks`
- `chore(repo): configure uv and ruff`


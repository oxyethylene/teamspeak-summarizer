# TeamSpeak Meeting Notes

Generate meeting-note style summaries from TeamSpeak `.wav` recordings in `voice_record/`.

## Features

- Parse TeamSpeak filename metadata to identify speaker and recording start time.
- Support both `playback_*` and `capture_*` files.
- Use `--recording-starter` to label `capture_*` track speaker.
- Probe audio with `ffprobe` (from ffmpeg).
- Optional preprocess: bundle all input wav tracks into one multitrack `.mka` container.
- Transcribe with local `whisper` CLI or OpenAI cloud (`hybrid` mode supported).
- Summarize via Ollama OpenAI-compatible endpoint (default `http://192.168.10.60:11434/v1`).
- Merge multi-track segments into one timeline and produce Markdown meeting notes.

## Requirements

- Python 3.12+
- `uv`
- `ffmpeg` (must include `ffprobe`)
- Optional for cloud ASR transcription fallback: `OPENAI_API_KEY`
- Optional for local ASR: `whisper` CLI in `PATH`
- Optional for Ollama auth/customization: `OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

## Setup

```bash
uv sync --all-groups
```

## Run

```bash
uv run teamspeak-meeting-notes \
	--audio-dir voice_record \
	--recording-starter 曾庆宝 \
	--bundle-multitrack \
	--asr-mode hybrid \
	--language zh \
	--meeting-title "TeamSpeak 日会"
```

Output Markdown will be written into `output/`.

### Ollama summarization settings

The summary step uses Ollama by default through OpenAI-compatible API.

Defaults:

- `OLLAMA_BASE_URL=http://192.168.10.60:11434/v1`
- `OLLAMA_MODEL=glm-4.7-flash:q4_K_M`
- `OLLAMA_API_KEY=ollama`

Override example:

```bash
export OLLAMA_BASE_URL=http://192.168.10.60:11434/v1
export OLLAMA_MODEL=ministral-3:14b
export OLLAMA_API_KEY=ollama
uv run teamspeak-meeting-notes --audio-dir voice_record_5m --recording-starter 曾庆宝
```

### Bundle only (preprocess only)

```bash
uv run teamspeak-meeting-notes \
	--audio-dir voice_record \
	--recording-starter 曾庆宝 \
	--bundle-only
```

This creates `output/multitrack_<meeting>.mka` where each speaker/file is a separate audio stream.

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


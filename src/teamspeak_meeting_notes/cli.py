from __future__ import annotations

import argparse
from pathlib import Path

from teamspeak_meeting_notes.pipeline import PipelineConfig, run_pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="teamspeak-meeting-notes",
        description="Generate meeting-note style summary from TeamSpeak wav recordings.",
    )
    parser.add_argument("--audio-dir", type=Path, default=Path("voice_record"))
    parser.add_argument(
        "--recording-starter",
        type=str,
        default=None,
        help="Required when capture_*.wav exists; used as speaker label for capture tracks.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument(
        "--asr-mode",
        choices=("local", "cloud", "hybrid"),
        default="hybrid",
        help="local=whisper CLI, cloud=OpenAI API, hybrid=local then cloud fallback.",
    )
    parser.add_argument("--language", type=str, default=None, help="ASR language hint, e.g. zh")
    parser.add_argument("--meeting-title", type=str, default=None)
    return parser


def run_cli() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    config = PipelineConfig(
        audio_dir=args.audio_dir,
        recording_starter=args.recording_starter,
        output_dir=args.output_dir,
        asr_mode=args.asr_mode,
        language=args.language,
        meeting_title=args.meeting_title,
    )

    out = run_pipeline(config)
    print(f"Meeting note written to: {out}")

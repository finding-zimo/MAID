"""MAID CLI entrypoint.

Usage:
    python -m maid [options]
    maid [options]          # if installed via pip

Options:
    --mode MODE         Personality mode: commentator, coach, friend
    --config PATH       Path to config TOML file (default: ./config.toml)
    --interval SECS     Seconds between analysis cycles
    --tts PROVIDER      TTS provider: elevenlabs, openai, pyttsx3
    --monitor INDEX     Monitor index to capture (0 = primary)
    --model MODEL       Claude model ID
    --mock              Run without API keys (canned responses + pyttsx3 TTS)
    --list-monitors     Print available monitors and exit
    -v, --verbose       Enable debug logging
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="maid",
        description="MAID — Medium-Agnostic AI Duo: a real-time AI companion for gaming.",
    )
    p.add_argument("--mode", choices=["commentator", "coach", "friend"], help="Personality mode")
    p.add_argument("--config", default="config.toml", help="Path to config TOML file")
    p.add_argument("--interval", type=float, dest="capture_interval_seconds", help="Seconds between analysis cycles")
    p.add_argument("--tts", dest="tts_provider", choices=["elevenlabs", "openai", "pyttsx3"], help="TTS provider")
    p.add_argument("--monitor", type=int, dest="monitor_index", help="Monitor index to capture")
    p.add_argument("--model", help="Claude model ID")
    p.add_argument("--voice", dest="macos_voice", help="macOS voice name for pyttsx3 TTS (e.g. 'Bad News', 'Zarvox'). Run: say -v '?' to list options")
    p.add_argument("--wait-for-tts", action="store_true", dest="wait_for_tts", help="Start the capture interval after TTS finishes, not before")
    p.add_argument("--mock", action="store_true", help="Run without API keys (canned responses + pyttsx3 TTS)")
    p.add_argument("--list-monitors", action="store_true", help="Print available monitors and exit")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return p


def list_monitors() -> None:
    import mss
    with mss.mss() as sct:
        monitors = sct.monitors[1:]  # skip index 0 (all-monitors combined)
        print(f"Available monitors ({len(monitors)}):")
        for i, m in enumerate(monitors):
            print(f"  [{i}] {m['width']}x{m['height']} at ({m['left']}, {m['top']})")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_monitors:
        list_monitors()
        return

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy library loggers unless in verbose mode.
    if not args.verbose:
        for lib in ("httpx", "httpcore", "anthropic", "openai", "elevenlabs", "urllib3"):
            logging.getLogger(lib).setLevel(logging.WARNING)

    from maid import config as cfg

    settings = cfg.load(args.config)

    # Apply CLI overrides.
    for attr in ("mode", "capture_interval_seconds", "tts_provider", "monitor_index", "model"):
        value = getattr(args, attr, None)
        if value is not None:
            setattr(settings, attr, value)

    if args.macos_voice:
        settings.macos_voice = args.macos_voice
    if args.wait_for_tts:
        settings.wait_for_tts = True

    if args.mock:
        settings.mock = True
        # Default to offline TTS in mock mode unless the user explicitly chose a provider.
        if args.tts_provider is None:
            settings.tts_provider = "pyttsx3"

    try:
        cfg.validate(settings)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    ai_label = "mock" if settings.mock else settings.model
    print(f"Starting MAID — mode: {settings.mode}, TTS: {settings.tts_provider}, AI: {ai_label}")
    print(f"  Capture interval: {settings.capture_interval_seconds}s  (override with --interval SECS)")

    from maid.capture.audio import AudioCapture
    from maid.capture.screen import ScreenCapture
    from maid.pipeline import loop
    from maid.tts.factory import build_tts

    screen = ScreenCapture(settings)
    audio = AudioCapture(settings)

    if settings.mock:
        from maid.ai.mock_client import MockAIClient
        ai = MockAIClient(settings)
    elif settings.model.startswith("gemini") or settings.model.startswith("gemma"):
        from maid.ai.gemini_client import GeminiClient
        ai = GeminiClient(settings)
    else:
        from maid.ai.client import AIClient
        ai = AIClient(settings)

    try:
        tts = build_tts(settings)
    except Exception as e:
        print(f"TTS initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

    screen.start()
    audio.start()

    try:
        asyncio.run(loop.run(settings, screen, audio, ai, tts))
    except KeyboardInterrupt:
        print("\nStopping MAID.")
    finally:
        screen.stop()
        audio.stop()


if __name__ == "__main__":
    main()

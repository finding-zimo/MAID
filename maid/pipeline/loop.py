"""Main async processing loop: capture → analyze → speak."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from maid.utils.image import encode_frame

if TYPE_CHECKING:
    from maid.ai.client import AIClient
    from maid.capture.audio import AudioCapture
    from maid.capture.screen import ScreenCapture
    from maid.config import Settings
    from maid.tts.base import TTSProvider

logger = logging.getLogger(__name__)


async def run(
    settings: Settings,
    screen: ScreenCapture,
    audio: AudioCapture,
    ai: AIClient,
    tts: TTSProvider,
) -> None:
    """Run the main analysis loop until interrupted.

    The loop is intentionally sequential:
      1. Grab the latest captured frame.
      2. Encode it (resize + JPEG compress).
      3. Send to Claude for analysis (blocking, run in thread pool).
      4. Speak the response (blocking, run in thread pool).
      5. Wait for the next iteration.

    Sequential execution prevents commentary from racing ahead of gameplay
    and keeps the state machine simple. The capture thread runs independently
    and always has a fresh frame ready.
    """
    print(
        f"\n  MAID is running in [{settings.mode.upper()}] mode.\n"
        f"  Press Ctrl+C to stop.\n"
    )

    frame_count = 0

    while True:
        loop_start = time.monotonic()

        # 1. Grab frame
        png_bytes = screen.get_latest()
        if png_bytes is None:
            logger.debug("No frame yet, waiting...")
            await asyncio.sleep(0.5)
            continue

        frame_count += 1
        logger.debug("Processing frame %d", frame_count)

        # 2. Encode
        try:
            frame_b64 = await asyncio.to_thread(encode_frame, png_bytes)
        except Exception:
            logger.exception("Failed to encode frame %d", frame_count)
            await asyncio.sleep(1)
            continue

        # 3. Analyze
        audio_hint = audio.get_hint()
        try:
            response_text = await asyncio.to_thread(ai.analyze_frame, frame_b64, audio_hint)
            logger.info("[%s] %s", settings.mode, response_text)
        except Exception:
            logger.exception("AI analysis failed for frame %d", frame_count)
            await asyncio.sleep(2)
            continue

        # 4. Speak
        try:
            await asyncio.to_thread(tts.speak, response_text)
        except Exception:
            logger.exception("TTS failed")

        # 5. Wait for the remainder of the capture interval.
        elapsed = time.monotonic() - loop_start
        sleep_time = max(0.0, settings.capture_interval_seconds - elapsed)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

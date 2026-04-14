"""Main async processing loop: capture → analyze → speak."""

from __future__ import annotations

import asyncio
import logging
import re
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
        except Exception as exc:
            # On rate-limit errors, respect the suggested retry delay so we
            # don't hammer the API and burn through the per-minute quota.
            wait = _parse_retry_delay(str(exc))
            if wait:
                logger.warning("Rate limited — waiting %ds before next frame", wait)
                await asyncio.sleep(wait)
            else:
                logger.exception("AI analysis failed for frame %d", frame_count)
                await asyncio.sleep(2)
            continue

        # 4. Speak (skip if the AI decided nothing notable is happening)
        if response_text == "[SILENT]":
            logger.debug("Frame %d: no notable action, staying silent", frame_count)
        else:
            logger.info("[%s] %s", settings.mode, response_text)
            try:
                await asyncio.to_thread(tts.speak, response_text)
            except Exception:
                logger.exception("TTS failed")

            # In wait_for_tts mode the interval is measured from when speech
            # finishes, guaranteeing a full gap before the next frame is sent.
            if settings.wait_for_tts:
                loop_start = time.monotonic()

        # 5. Wait for the remainder of the capture interval.
        elapsed = time.monotonic() - loop_start
        sleep_time = max(0.0, settings.capture_interval_seconds - elapsed)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)


def _parse_retry_delay(error_message: str) -> int:
    """Extract the retry delay in seconds from a rate-limit error message.

    Returns 0 if no delay is found (i.e. the error is not a rate-limit error).
    Adds a small buffer to avoid immediately hitting the limit again.
    """
    match = re.search(r"retryDelay['\"]:\s*['\"](\d+)s", error_message)
    if match:
        return int(match.group(1)) + 2
    # Fall back to a 60-second wait for any 429 error without a stated delay.
    if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
        return 62
    return 0

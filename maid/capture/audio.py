"""Microphone audio capture via sounddevice.

v1 implementation: captures a short chunk and returns a simple boolean
indicating whether the player is speaking (RMS above threshold). This is
passed to the AI as a contextual hint without requiring Whisper transcription.

TODO: Upgrade path — replace _is_speaking() with a Whisper transcription call
      so the AI can hear what the player says and respond to it directly.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from maid.config import Settings

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000     # Hz
CHUNK_SECONDS = 1.5      # How much audio to sample per poll
SPEAKING_THRESHOLD = 0.01  # RMS level above which we consider the player speaking


class AudioCapture:
    """Polls the microphone and exposes a simple 'is player speaking' flag."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.audio_enabled
        self._speaking = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self._enabled:
            return
        try:
            import sounddevice as sd  # noqa: F401 — validate import before starting thread
        except ImportError:
            logger.warning("sounddevice not installed; audio capture disabled.")
            self._enabled = False
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="audio-capture")
        self._thread.start()
        logger.debug("Audio capture started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def get_hint(self) -> str:
        """Return a natural-language hint about the player's audio state."""
        if not self._enabled:
            return ""
        with self._lock:
            return "(the player is speaking)" if self._speaking else ""

    def _capture_loop(self) -> None:
        import sounddevice as sd

        while not self._stop_event.is_set():
            try:
                chunk = sd.rec(
                    int(CHUNK_SECONDS * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    blocking=True,
                )
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                with self._lock:
                    self._speaking = rms > SPEAKING_THRESHOLD

            except Exception:
                logger.exception("Audio capture error")
                time.sleep(1)

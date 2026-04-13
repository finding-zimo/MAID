"""pyttsx3 TTS provider — offline fallback, no API key required."""

from __future__ import annotations

import logging

from maid.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class Pyttsx3TTS(TTSProvider):
    def __init__(self) -> None:
        import pyttsx3
        self._engine = pyttsx3.init()
        # Slightly faster than default for a more lively feel.
        rate = self._engine.getProperty("rate")
        self._engine.setProperty("rate", int(rate * 1.1))

    def speak(self, text: str) -> None:
        logger.debug("pyttsx3 TTS: %r", text[:60])
        self._engine.say(text)
        self._engine.runAndWait()

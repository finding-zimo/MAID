"""pyttsx3 TTS provider — offline fallback, no API key required.

On macOS, pyttsx3's runAndWait() returns before speech completes when called
from a thread pool (known issue with the nsss driver). We use the built-in
`say` command instead, which blocks until the utterance finishes. pyttsx3 is
kept as a fallback for non-macOS platforms.
"""

from __future__ import annotations

import logging
import platform
import subprocess

from maid.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_IS_MACOS = platform.system() == "Darwin"


class Pyttsx3TTS(TTSProvider):
    def __init__(self) -> None:
        if not _IS_MACOS:
            import pyttsx3
            self._engine = pyttsx3.init()
            rate = self._engine.getProperty("rate")
            self._engine.setProperty("rate", int(rate * 1.1))

    def speak(self, text: str) -> None:
        logger.debug("TTS: %r", text[:60])
        if _IS_MACOS:
            subprocess.run(["say", text], check=False)
        else:
            self._engine.say(text)
            self._engine.runAndWait()

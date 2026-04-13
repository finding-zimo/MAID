"""Abstract TTS provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSProvider(ABC):
    """Synchronous text-to-speech interface.

    ``speak()`` blocks until audio playback is complete (or fires-and-forgets
    depending on the implementation). The pipeline calls this from a thread
    pool via ``asyncio.to_thread()``.
    """

    @abstractmethod
    def speak(self, text: str) -> None:
        """Convert text to speech and play it."""
        ...

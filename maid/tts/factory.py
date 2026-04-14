"""Build the correct TTSProvider from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maid.tts.base import TTSProvider

if TYPE_CHECKING:
    from maid.config import Settings


def build_tts(settings: Settings) -> TTSProvider:
    provider = settings.tts_provider
    if provider == "elevenlabs":
        from maid.tts.elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS(settings)
    if provider == "openai":
        from maid.tts.openai_tts import OpenAITTS
        return OpenAITTS(settings)
    if provider == "pyttsx3":
        from maid.tts.pyttsx3_tts import Pyttsx3TTS
        return Pyttsx3TTS(settings)
    raise ValueError(f"Unknown TTS provider: {provider!r}")

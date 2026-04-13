"""ElevenLabs TTS provider — highest quality, streaming audio."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from maid.tts.base import TTSProvider

if TYPE_CHECKING:
    from maid.config import Settings

logger = logging.getLogger(__name__)


class ElevenLabsTTS(TTSProvider):
    def __init__(self, settings: Settings) -> None:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import play

        self._play = play
        self._client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        self._voice_id = settings.elevenlabs_voice_id

    def speak(self, text: str) -> None:
        logger.debug("ElevenLabs TTS: %r", text[:60])
        audio = self._client.text_to_speech.convert(
            voice_id=self._voice_id,
            text=text,
            model_id="eleven_turbo_v2",  # lowest latency model
            output_format="mp3_44100_128",
        )
        self._play(audio)

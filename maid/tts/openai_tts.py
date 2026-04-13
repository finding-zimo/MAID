"""OpenAI TTS provider — high quality, good latency."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from maid.tts.base import TTSProvider

if TYPE_CHECKING:
    from maid.config import Settings

logger = logging.getLogger(__name__)


class OpenAITTS(TTSProvider):
    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._voice = settings.openai_voice

    def speak(self, text: str) -> None:
        logger.debug("OpenAI TTS: %r", text[:60])
        response = self._client.audio.speech.create(
            model="tts-1",
            voice=self._voice,
            input=text,
            response_format="mp3",
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = Path(f.name)
            response.stream_to_file(tmp_path)

        try:
            _play_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)


def _play_file(path: Path) -> None:
    """Play an audio file using a platform-appropriate command."""
    import sys
    if sys.platform == "darwin":
        subprocess.run(["afplay", str(path)], check=True)
    elif sys.platform.startswith("linux"):
        # Try mpg123 first, fall back to aplay (requires conversion)
        try:
            subprocess.run(["mpg123", "-q", str(path)], check=True)
        except FileNotFoundError:
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)], check=True)
    else:
        # Windows
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME)

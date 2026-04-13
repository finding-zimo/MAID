"""Anthropic API client with prompt caching and rolling context window."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import anthropic

from maid.ai.personalities import PERSONALITIES

if TYPE_CHECKING:
    from maid.config import Settings

logger = logging.getLogger(__name__)

# Number of prior (assistant, user) turn pairs to keep as context.
CONTEXT_WINDOW_TURNS = 3


class AIClient:
    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.model
        self._max_tokens = settings.max_tokens
        self._mode = settings.mode
        self._system_prompt = PERSONALITIES[settings.mode]

        # Rolling context: list of {"role": ..., "content": str} message dicts.
        # Only text entries — we don't re-send old images.
        self._context: list[dict] = []

    def analyze_frame(self, frame_b64: str, audio_hint: str = "") -> str:
        """Send the current frame to Claude and return the spoken response text.

        Args:
            frame_b64: Base64-encoded JPEG of the current game frame.
            audio_hint: Optional string describing mic audio state, e.g.
                        "(player is speaking)" or empty string.
        """
        user_text = "What do you see happening in this gameplay? React in character."
        if audio_hint:
            user_text += f" Note: {audio_hint}"

        messages = [
            *self._context_tail(),
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": frame_b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            },
        ]

        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {
                    "type": "text",
                    "text": self._system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )

        reply = response.content[0].text.strip()

        # Log cache performance on the first call and periodically.
        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_write = getattr(usage, "cache_creation_input_tokens", 0)
        if cache_write:
            logger.debug("Prompt cache written (%d tokens)", cache_write)
        elif cache_read:
            logger.debug("Prompt cache hit (%d tokens saved)", cache_read)

        self._append_context(user_text, reply)
        return reply

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _context_tail(self) -> list[dict]:
        """Return the last N turns as plain-text messages (no images)."""
        return self._context[-(CONTEXT_WINDOW_TURNS * 2):]

    def _append_context(self, user_text: str, assistant_text: str) -> None:
        self._context.append({"role": "user", "content": user_text})
        self._context.append({"role": "assistant", "content": assistant_text})
        # Cap total stored turns to avoid unbounded growth.
        max_messages = CONTEXT_WINDOW_TURNS * 2 * 2
        if len(self._context) > max_messages:
            self._context = self._context[-max_messages:]

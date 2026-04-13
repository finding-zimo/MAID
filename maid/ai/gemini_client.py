"""Google Gemini API client — drop-in replacement for AIClient.

Uses the google-genai SDK. Gemini 2.0 Flash is free-tier eligible and
supports vision input, making it the recommended model for development.
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from maid.ai.personalities import PERSONALITIES

if TYPE_CHECKING:
    from maid.config import Settings

logger = logging.getLogger(__name__)

CONTEXT_WINDOW_TURNS = 3


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.model
        self._max_tokens = settings.max_tokens
        self._system_prompt = PERSONALITIES[settings.mode]

        # Rolling context: list of (user_text, model_text) string pairs.
        # Images are not re-sent — only the text of prior turns.
        self._context: list[tuple[str, str]] = []

    def analyze_frame(self, frame_b64: str, audio_hint: str = "") -> str:
        """Send the current frame to Gemini and return the spoken response text."""
        from google.genai import types

        user_text = "What do you see happening in this gameplay? React in character."
        if audio_hint:
            user_text += f" Note: {audio_hint}"

        contents: list = []

        # Prepend recent context turns (text only, no images).
        for prior_user, prior_model in self._context[-CONTEXT_WINDOW_TURNS:]:
            contents.append(types.Content(role="user", parts=[types.Part(text=prior_user)]))
            contents.append(types.Content(role="model", parts=[types.Part(text=prior_model)]))

        # Current turn with the screenshot.
        image_bytes = base64.b64decode(frame_b64)
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    types.Part(text=user_text),
                ],
            )
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=self._system_prompt,
                max_output_tokens=self._max_tokens,
            ),
        )

        reply = response.text.strip()
        logger.debug("Gemini response (%d chars)", len(reply))

        self._context.append((user_text, reply))
        if len(self._context) > CONTEXT_WINDOW_TURNS:
            self._context = self._context[-CONTEXT_WINDOW_TURNS:]

        return reply

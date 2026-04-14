"""Mock AI client for testing without an Anthropic API key.

Returns pre-written responses that cycle through each personality's
characteristic voice. Includes a small simulated delay so the pipeline
behaves realistically during testing.
"""

from __future__ import annotations

import itertools
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maid.config import Settings

# Simulated API round-trip time (seconds). Keeps the loop feel realistic.
MOCK_DELAY = 0.8

_RESPONSES: dict[str, list[str]] = {
    "commentator": [
        "AND WE ARE LIVE! The competitor has control of the screen — let's see what they do with it!",
        "Methodical movement here, they're setting up — this looks calculated, folks.",
        "OH! A bold decision! The crowd is on the edge of their seats right now!",
        "Look at that positioning — textbook macro play from our competitor!",
        "They're taking their time, composure under pressure — a true sign of a seasoned player.",
        "INCREDIBLE resource management on display! This player does NOT miss a beat!",
        "A slight misstep there — but they recover! The resilience is UNREAL!",
        "Setting up for something big here — I can feel the tension building in the arena!",
        "Clean mechanics, efficient pathing — this is what peak gameplay looks like, ladies and gentlemen!",
        "And the crowd goes absolutely WILD as our player navigates this flawlessly!",
        "Wait — they're going in! They're committed! LET'S SEE HOW THIS PLAYS OUT!",
        "That is some elite-level decision making right there — the analysts in the booth are going to LOVE this one.",
    ],
    "coach": [
        "Good positioning there. Keep an eye on the edges of the screen — there may be threats you're not seeing.",
        "You want to be thinking about your next objective right now, not reacting.",
        "Slow down. You're moving too fast to gather information — pace yourself.",
        "That resource pickup was solid. Now prioritize consolidating before you push further.",
        "Watch your exposure — you're presenting yourself as a target. Reposition to the right.",
        "Good call. Now think two steps ahead — what comes after this?",
        "You're doing fine, but you're leaving value on the table. Be more decisive.",
        "Check your surroundings before committing. Information first, action second.",
        "Nice recovery. Now reset and play from a position of strength.",
        "You have the advantage here — press it. Don't give them time to breathe.",
        "Slow down at transitions. That's where most mistakes happen.",
        "That was the right read. Trust your instincts and keep that up.",
    ],
    "friend": [
        "You're actually inting right now. Like, genuinely inting.",
        "No way you just trolled that. No WAY.",
        "Delete the game. I'm being serious, just uninstall.",
        "Broken clock moment — that was fine. Don't get used to hearing that.",
        "Bro has the game sense of a level 1 account, I'm not even joking.",
        "I've seen bots play better than this. Actual bots.",
        "That is HARDSTUCK behavior and you know it.",
        "How. HOW. Explain yourself right now.",
        "You are the reason people go AFK. You know that, right?",
        "Okay fine, that was clean. Don't let it go to your head.",
        "Criminally bad. Like, reportable. I would report you.",
        "I am physically in pain watching this. Physically.",
    ],
}


class MockAIClient:
    """Drop-in replacement for AIClient that needs no API key."""

    def __init__(self, settings: Settings) -> None:
        self._mode = settings.mode
        self._cycle = itertools.cycle(_RESPONSES[settings.mode])

    def analyze_frame(self, frame_b64: str, audio_hint: str = "") -> str:
        time.sleep(MOCK_DELAY)
        return next(self._cycle)

"""Configuration loading with TOML file + environment variable overrides."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


TTS_PROVIDER = Literal["elevenlabs", "openai", "pyttsx3"]
PERSONALITY_MODE = Literal["commentator", "coach", "friend"]


@dataclass
class Settings:
    # API keys
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    openai_api_key: str = ""

    # Session
    mode: PERSONALITY_MODE = "commentator"
    capture_interval_seconds: float = 4.0
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 150

    # Capture
    monitor_index: int = 0
    audio_enabled: bool = False

    # TTS
    tts_provider: TTS_PROVIDER = "elevenlabs"
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    openai_voice: str = "nova"

    # Mock mode — no API keys required, uses canned responses + pyttsx3
    mock: bool = False


def load(path: str | Path = "config.toml") -> Settings:
    """Load settings from a TOML file, then apply environment variable overrides."""
    settings = Settings()

    config_path = Path(path)
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        api = data.get("api", {})
        session = data.get("session", {})
        capture = data.get("capture", {})
        tts = data.get("tts", {})

        settings.anthropic_api_key = api.get("anthropic_api_key", settings.anthropic_api_key)
        settings.elevenlabs_api_key = api.get("elevenlabs_api_key", settings.elevenlabs_api_key)
        settings.openai_api_key = api.get("openai_api_key", settings.openai_api_key)

        settings.mode = session.get("mode", settings.mode)
        settings.capture_interval_seconds = float(
            session.get("capture_interval_seconds", settings.capture_interval_seconds)
        )
        settings.model = session.get("model", settings.model)
        settings.max_tokens = int(session.get("max_tokens", settings.max_tokens))

        settings.monitor_index = int(capture.get("monitor_index", settings.monitor_index))
        settings.audio_enabled = bool(capture.get("audio_enabled", settings.audio_enabled))

        settings.tts_provider = tts.get("provider", settings.tts_provider)
        settings.elevenlabs_voice_id = tts.get("elevenlabs_voice_id", settings.elevenlabs_voice_id)
        settings.openai_voice = tts.get("openai_voice", settings.openai_voice)

    # Environment variable overrides
    env_map = {
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "ELEVENLABS_API_KEY": "elevenlabs_api_key",
        "OPENAI_API_KEY": "openai_api_key",
        "MAID_MODE": "mode",
        "MAID_TTS_PROVIDER": "tts_provider",
        "MAID_MODEL": "model",
    }
    for env_var, attr in env_map.items():
        value = os.environ.get(env_var)
        if value:
            setattr(settings, attr, value)

    return settings


def validate(settings: Settings) -> None:
    """Raise ValueError for any fatal misconfiguration."""
    if settings.mode not in ("commentator", "coach", "friend"):
        raise ValueError(f"Unknown mode '{settings.mode}'. Choose: commentator, coach, friend")

    if settings.tts_provider not in ("elevenlabs", "openai", "pyttsx3"):
        raise ValueError(
            f"Unknown tts_provider '{settings.tts_provider}'. Choose: elevenlabs, openai, pyttsx3"
        )

    # In mock mode, all API keys are optional.
    if settings.mock:
        return

    if not settings.anthropic_api_key:
        raise ValueError(
            "anthropic_api_key is required. Set it in config.toml under [api] "
            "or via the ANTHROPIC_API_KEY environment variable. "
            "(Use --mock to run without any API keys.)"
        )

    if settings.tts_provider == "elevenlabs" and not settings.elevenlabs_api_key:
        raise ValueError(
            "elevenlabs_api_key is required when tts_provider = 'elevenlabs'. "
            "Set it in config.toml or use ELEVENLABS_API_KEY env var."
        )

    if settings.tts_provider == "openai" and not settings.openai_api_key:
        raise ValueError(
            "openai_api_key is required when tts_provider = 'openai'. "
            "Set it in config.toml or use OPENAI_API_KEY env var."
        )

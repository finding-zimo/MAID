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
    gemini_api_key: str = ""
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


def _apply_toml(settings: Settings, path: Path) -> None:
    """Merge a TOML file's values into settings. Missing file is silently ignored."""
    if not path.exists():
        return
    with open(path, "rb") as f:
        data = tomllib.load(f)

    api = data.get("api", {})
    session = data.get("session", {})
    capture = data.get("capture", {})
    tts = data.get("tts", {})

    if "anthropic_api_key" in api:
        settings.anthropic_api_key = api["anthropic_api_key"]
    if "gemini_api_key" in api:
        settings.gemini_api_key = api["gemini_api_key"]
    if "elevenlabs_api_key" in api:
        settings.elevenlabs_api_key = api["elevenlabs_api_key"]
    if "openai_api_key" in api:
        settings.openai_api_key = api["openai_api_key"]

    if "mode" in session:
        settings.mode = session["mode"]
    if "capture_interval_seconds" in session:
        settings.capture_interval_seconds = float(session["capture_interval_seconds"])
    if "model" in session:
        settings.model = session["model"]
    if "max_tokens" in session:
        settings.max_tokens = int(session["max_tokens"])

    if "monitor_index" in capture:
        settings.monitor_index = int(capture["monitor_index"])
    if "audio_enabled" in capture:
        settings.audio_enabled = bool(capture["audio_enabled"])

    if "provider" in tts:
        settings.tts_provider = tts["provider"]
    if "elevenlabs_voice_id" in tts:
        settings.elevenlabs_voice_id = tts["elevenlabs_voice_id"]
    if "openai_voice" in tts:
        settings.openai_voice = tts["openai_voice"]


def load(path: str | Path = "config.toml") -> Settings:
    """Load settings from a TOML file, then apply environment variable overrides.

    If a ``config.local.toml`` file exists next to the main config file, it is
    loaded afterwards and its values take precedence. Use it for API keys and
    other secrets that should not be committed to version control.
    """
    settings = Settings()
    config_path = Path(path)
    _apply_toml(settings, config_path)

    # Local override file — gitignored, safe for secrets.
    local_path = config_path.parent / (config_path.stem + ".local.toml")
    _apply_toml(settings, local_path)

    # Environment variable overrides
    env_map = {
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "GEMINI_API_KEY": "gemini_api_key",
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

    is_gemini = settings.model.startswith("gemini")

    if is_gemini and not settings.gemini_api_key:
        raise ValueError(
            "gemini_api_key is required when using a Gemini model. Set it in config.toml "
            "under [api] or via the GEMINI_API_KEY environment variable."
        )

    if not is_gemini and not settings.anthropic_api_key:
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

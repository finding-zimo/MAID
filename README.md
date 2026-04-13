# MAID — Medium-Agnostic AI Duo

A real-time AI companion for gaming. MAID captures your screen while you play, analyzes what's happening using Claude's vision model, and speaks commentary back to you through a voice model — all in character.

Three built-in personality modes:

- **Commentator** — an eSports shoutcaster named APEX who treats every session like a world championship broadcast
- **Coach** — a calm tactical analyst named AXIOM who gives concise, actionable real-time advice
- **Friend** — BUDDY, your best friend watching over your shoulder, equal parts hype and affectionate trash talk

---

## How it works

```
screen capture (background thread)
        |
        v
  latest frame (PNG)
        |
        v
  resize + JPEG encode       <- Pillow, reduces payload ~10x vs raw PNG
        |
        v
  Claude vision API          <- claude-sonnet-4-6 with prompt caching
        |
        v
  spoken response            <- ElevenLabs / OpenAI TTS / pyttsx3
```

The loop is sequential — analyze then speak, then repeat. This prevents commentary from racing ahead of gameplay. The screen capture thread runs independently, so the analysis always gets the freshest available frame.

**Prompt caching** — the personality system prompt is sent with `cache_control: ephemeral`. After the first API call it's served from Anthropic's cache, cutting input token costs by ~90% for every subsequent frame.

---

## Requirements

- Python 3.11+
- macOS, Linux, or Windows
- An Anthropic API key (for real usage)
- A TTS API key — ElevenLabs or OpenAI — or none at all (use the offline `pyttsx3` fallback)

---

## Installation

```bash
git clone <repo-url>
cd maid

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e .
```

> **Linux only:** PortAudio is required for mic capture.
> ```bash
> sudo apt install portaudio19-dev   # Debian/Ubuntu
> sudo dnf install portaudio-devel   # Fedora
> ```

---

## Configuration

Copy `config.toml` and fill in your API keys:

```toml
[api]
anthropic_api_key = "sk-ant-..."
elevenlabs_api_key = "..."          # only needed if tts.provider = "elevenlabs"
openai_api_key = "sk-..."           # only needed if tts.provider = "openai"

[session]
mode = "commentator"                # commentator | coach | friend
capture_interval_seconds = 4.0     # how often to analyze a frame
model = "claude-sonnet-4-6"         # or claude-opus-4-6 for stronger vision
max_tokens = 150                    # keep low — responses are spoken aloud

[capture]
monitor_index = 0                   # 0 = primary monitor
audio_enabled = false               # mic speaking hint (no transcription)

[tts]
provider = "elevenlabs"             # elevenlabs | openai | pyttsx3
elevenlabs_voice_id = "EXAVITQu4vr4xnSDxMaL"   # Rachel (default)
openai_voice = "nova"               # alloy | echo | fable | onyx | nova | shimmer
```

All keys can also be set via environment variables, which override `config.toml`:

| Variable | Setting |
|---|---|
| `ANTHROPIC_API_KEY` | `api.anthropic_api_key` |
| `ELEVENLABS_API_KEY` | `api.elevenlabs_api_key` |
| `OPENAI_API_KEY` | `api.openai_api_key` |
| `MAID_MODE` | `session.mode` |
| `MAID_TTS_PROVIDER` | `tts.provider` |
| `MAID_MODEL` | `session.model` |

---

## Running MAID

```bash
# Start with defaults from config.toml
maid

# Choose a personality mode
maid --mode commentator
maid --mode coach
maid --mode friend

# Change capture interval (seconds between analysis cycles)
maid --interval 3.0

# Use a different TTS provider
maid --tts openai
maid --tts pyttsx3

# Capture a secondary monitor
maid --list-monitors          # see available monitors
maid --monitor 1

# Use the more capable vision model
maid --model claude-opus-4-6

# Verbose logging (shows API cache stats, frame timings)
maid --verbose

# Point at a different config file
maid --config ~/my-config.toml
```

CLI flags always take priority over `config.toml`.

---

## Testing without API keys

Use `--mock` to run the full pipeline — screen capture, frame encoding, the processing loop, and TTS — with zero API credentials:

```bash
maid --mock                          # commentator mode, pyttsx3 TTS
maid --mock --mode coach
maid --mock --mode friend
maid --mock --interval 1.5           # faster cycling to preview quickly
```

`--mock` replaces the Claude API call with pre-written in-character responses that cycle in order. TTS defaults to `pyttsx3` (offline, no key needed). You can combine `--mock` with `--tts elevenlabs` if you have a TTS key but not an Anthropic key.

---

## CLI reference

```
usage: maid [-h] [--mode {commentator,coach,friend}]
            [--config CONFIG]
            [--interval SECONDS]
            [--tts {elevenlabs,openai,pyttsx3}]
            [--monitor INDEX]
            [--model MODEL]
            [--mock]
            [--list-monitors]
            [-v]

options:
  --mode          Personality mode (default: from config.toml)
  --config        Path to TOML config file (default: ./config.toml)
  --interval      Seconds between analysis cycles (default: 4.0)
  --tts           TTS provider: elevenlabs, openai, or pyttsx3
  --monitor       Monitor index to capture (default: 0)
  --model         Claude model ID
  --mock          Run without API keys (canned responses + pyttsx3)
  --list-monitors Print available monitors and exit
  -v, --verbose   Enable debug logging
```

---

## Tuning

**Commentary feels too fast / too slow**
Adjust `capture_interval_seconds`. 3–4 seconds is good for fast-paced games; 6–8 works better for strategy games with slower tempo.

**Responses are too long and TTS lags behind**
Lower `max_tokens` in `config.toml`. 100–150 tokens produces 1–2 spoken sentences, which lands cleanly in a 3–5 second window.

**Vision analysis is missing details**
Switch to `model = "claude-opus-4-6"`. It has stronger visual reasoning at roughly 3× the cost of Sonnet.

**Reducing API cost**
The personality system prompt is prompt-cached after the first call, so the main ongoing cost is the image tokens per frame. The frame encoder caps images at 1280px on the longest side and compresses to JPEG quality 80, which significantly reduces token usage compared to sending raw screenshots.

**Multi-monitor setups**
Run `maid --list-monitors` to see indices, then use `--monitor 1` (or whichever index) to capture a specific screen.

---

## Project structure

```
maid/
├── config.toml               User configuration (API keys, mode, etc.)
├── pyproject.toml
└── maid/
    ├── main.py               CLI entrypoint (argparse)
    ├── config.py             Config loading — TOML + env var overrides
    ├── capture/
    │   ├── screen.py         Screen capture via mss (background thread)
    │   └── audio.py          Mic capture via sounddevice (speaking hint)
    ├── ai/
    │   ├── client.py         Anthropic client with prompt caching
    │   ├── mock_client.py    Mock client for testing without API keys
    │   └── personalities.py  System prompts for each mode
    ├── tts/
    │   ├── base.py           Abstract TTSProvider interface
    │   ├── elevenlabs_tts.py ElevenLabs implementation
    │   ├── openai_tts.py     OpenAI TTS implementation
    │   ├── pyttsx3_tts.py    Offline fallback
    │   └── factory.py        Builds the correct provider from settings
    ├── pipeline/
    │   └── loop.py           Async capture → analyze → speak loop
    └── utils/
        └── image.py          Frame resize + JPEG encoding
```

---

## Personalities

### APEX — Commentator

High-energy eSports shoutcaster. Treats every play like it's happening in front of a live arena crowd. Uses professional gaming vocabulary, builds narrative tension, and reacts with maximum enthusiasm to big moments and theatrical disbelief to mistakes.

### AXIOM — Coach

Calm, analytical, direct. Delivers one actionable insight per observation — no fluff. Focuses on positioning, resource management, decision timing, and risk-reward tradeoffs. Mixes correction with positive reinforcement.

### BUDDY — Friend

Your best friend sitting next to you. Casually supportive, but will absolutely roast you for bad plays — in love, of course. Uses gaming slang naturally, tracks the session narrative (bad streaks, redemption arcs), and reacts like a real person instead of a scripted commentator.

Personality system prompts live in `maid/ai/personalities.py` and can be edited directly to customize tone, vocabulary, or behavior.

---

## Troubleshooting

**`Configuration error: anthropic_api_key is required`**
Add your key to `config.toml` under `[api]`, set the `ANTHROPIC_API_KEY` environment variable, or use `--mock` to run without it.

**`TTS initialization failed`**
If using ElevenLabs or OpenAI TTS, verify the API key is set. Fall back to `--tts pyttsx3` to confirm the rest of the pipeline works.

**No audio output**
On macOS, `afplay` is used to play OpenAI TTS audio — it ships with the OS. On Linux, install `mpg123` (`apt install mpg123`) or `ffmpeg`. pyttsx3 uses the system TTS engine directly.

**Screen capture is black or wrong monitor**
Run `maid --list-monitors` and confirm the `--monitor` index. On some systems mss requires display permissions — on macOS, grant Screen Recording permission to Terminal (or your terminal app) in System Settings > Privacy & Security.

**High API costs**
Lower `capture_interval_seconds` less aggressively, reduce `max_tokens`, and confirm prompt caching is working by running with `--verbose` and watching for `Prompt cache hit` log lines after the first call.

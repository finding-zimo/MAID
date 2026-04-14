# MAID — Medium-Agnostic AI Duo

A real-time AI companion for gaming. MAID captures your screen while you play, analyzes what's happening using a vision model, and speaks commentary back to you — all in character, and only when something notable is actually happening.

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
  vision model API           <- Gemini (free tier) or Claude (paid)
        |
        v
  spoken response            <- ElevenLabs / OpenAI TTS / pyttsx3
```

The loop is sequential — analyze then speak, then repeat. The AI is instructed to respond with `[SILENT]` when nothing notable is happening, so commentary only fires on meaningful moments. The screen capture thread runs independently so analysis always gets the freshest available frame.

**Context memory** — the model remembers the last 3 notable moments. Before each new frame is sent, the text of up to 3 prior exchanges is prepended to the conversation, so the AI can reference what it said earlier ("called it before it happened", "you redeemed yourself from that last disaster"). Images are not re-sent — only the text of prior responses — so memory is cheap. Silent frames don't consume context slots. The window size can be adjusted by changing `CONTEXT_WINDOW_TURNS` in `maid/ai/gemini_client.py`.

---

## Requirements

- Python 3.11+
- macOS, Linux, or Windows
- A vision model API key — Google Gemini (free tier available) or Anthropic Claude (paid)
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

Edit `config.toml` with your API keys and preferences:

```toml
[api]
# Anthropic Claude (paid) — set if using a claude-* model
anthropic_api_key = ""

# Google Gemini — free tier available at https://aistudio.google.com
gemini_api_key = ""

# TTS providers — at least one required (or set tts.provider = "pyttsx3")
elevenlabs_api_key = ""
openai_api_key = ""

[session]
mode = "commentator"                # commentator | coach | friend
capture_interval_seconds = 15.0    # see Tuning section for guidance
model = "gemini-2.5-flash"          # or gemini-2.0-flash, claude-sonnet-4-6, etc.
max_tokens = 150                    # keep low — responses are spoken aloud
wait_for_tts = false                # see --wait-for-tts flag below

[capture]
monitor_index = 0                   # 0 = primary monitor
audio_enabled = false               # mic speaking hint (no transcription)

[tts]
provider = "pyttsx3"                # elevenlabs | openai | pyttsx3
elevenlabs_voice_id = "EXAVITQu4vr4xnSDxMaL"   # Rachel (default)
openai_voice = "nova"               # alloy | echo | fable | onyx | nova | shimmer
macos_voice = ""                    # macOS only — see pyttsx3 voices section below
```

### Secrets: config.local.toml

To avoid committing API keys to git, put them in `config.local.toml` (gitignored) instead. It is loaded after `config.toml` and its values take precedence:

```toml
# config.local.toml — never committed
[api]
gemini_api_key = "your-key-here"
```

### Environment variable overrides

All keys can also be set via environment variables, which override both config files:

| Variable | Setting |
|---|---|
| `ANTHROPIC_API_KEY` | `api.anthropic_api_key` |
| `GEMINI_API_KEY` | `api.gemini_api_key` |
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
maid --interval 15

# Use a specific AI model
maid --model gemini-2.5-flash
maid --model gemini-2.0-flash-lite
maid --model claude-sonnet-4-6

# Use a different TTS provider
maid --tts elevenlabs
maid --tts openai
maid --tts pyttsx3

# Wait for TTS to finish before starting the next capture interval
maid --wait-for-tts

# Capture a secondary monitor
maid --list-monitors          # see available monitors
maid --monitor 1

# Verbose logging (shows frame timings, debug info)
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
maid --mock --interval 2             # faster cycling to preview quickly
```

`--mock` replaces the AI API call with pre-written in-character responses that cycle in order. TTS defaults to `pyttsx3` (offline, no key needed). You can combine `--mock` with `--tts elevenlabs` if you have a TTS key but not an AI key.

---

## CLI reference

```
usage: maid [-h] [--mode {commentator,coach,friend}]
            [--config CONFIG]
            [--interval SECS]
            [--tts {elevenlabs,openai,pyttsx3}]
            [--monitor INDEX]
            [--model MODEL]
            [--wait-for-tts]
            [--mock]
            [--list-monitors]
            [-v]

options:
  --mode          Personality mode: commentator, coach, or friend
                  (default: from config.toml)
  --config        Path to TOML config file (default: ./config.toml)
  --interval      Seconds between analysis cycles (default: 15.0)
  --tts           TTS provider: elevenlabs, openai, or pyttsx3
  --monitor       Monitor index to capture (default: 0)
  --model         Vision model ID — any gemini-* or claude-* model
  --voice         macOS voice name for pyttsx3 TTS (e.g. "Bad News", "Zarvox").
                  Run `say -v '?'` to list all available voices.
  --wait-for-tts  Start the capture interval after TTS finishes, not before.
                  Ensures a full quiet gap after each line of commentary and
                  naturally reduces API call rate on free tier models.
  --mock          Run without API keys (canned responses + pyttsx3 TTS)
  --list-monitors Print available monitors and exit
  -v, --verbose   Enable debug logging
```

---

## Tuning

### Capture interval

The right interval depends on your AI model's rate limits:

| Tier | Model examples | Recommended interval |
|---|---|---|
| Gemini free tier | `gemini-2.5-flash`, `gemini-2.0-flash` | 15s (5 RPM limit) |
| Gemini paid | any Gemini model | 4–6s |
| Claude paid | `claude-sonnet-4-6`, `claude-opus-4-6` | 4–6s |

The Gemini free tier allows 5 requests per minute (1 per 12s). Silent frames still consume quota, so 15s gives comfortable headroom. Use `--wait-for-tts` alongside a shorter interval on paid tiers to let TTS length naturally pace the loop.

### --wait-for-tts

Without this flag, the capture interval is measured from the *start* of each loop iteration. If AI analysis + TTS together take longer than the interval, the next frame fires immediately.

With `--wait-for-tts`, the interval resets *after* TTS finishes — guaranteeing a full gap of silence before the next frame is sent. This is recommended on free tier models since it also reduces total API call rate.

### Response length

Lower `max_tokens` if TTS lags behind gameplay. 100–150 tokens produces 1–2 spoken sentences, which lands cleanly in a 3–8 second window.

### Vision model quality

Stronger models produce more accurate commentary. `gemini-2.5-flash` and `claude-opus-4-6` have the best visual reasoning; `gemini-2.0-flash-lite` is fastest and cheapest but may miss detail.

### Personality sensitivity

The threshold for what counts as "notable" is defined in the system prompts in `maid/ai/personalities.py`. Edit the `WHEN TO COMMENT vs STAY SILENT` section for each personality to make commentary more or less frequent.

---

## Project structure

```
maid/
├── config.toml               User configuration (API keys, mode, etc.)
├── config.local.toml         Local secrets — gitignored, overrides config.toml
├── pyproject.toml
└── maid/
    ├── main.py               CLI entrypoint (argparse)
    ├── config.py             Config loading — TOML + env var overrides
    ├── capture/
    │   ├── screen.py         Screen capture via mss (background thread)
    │   └── audio.py          Mic capture via sounddevice (speaking hint)
    ├── ai/
    │   ├── client.py         Anthropic/Claude client with prompt caching
    │   ├── gemini_client.py  Google Gemini client (free tier compatible)
    │   ├── mock_client.py    Mock client for testing without API keys
    │   └── personalities.py  System prompts for each mode
    ├── tts/
    │   ├── base.py           Abstract TTSProvider interface
    │   ├── elevenlabs_tts.py ElevenLabs implementation
    │   ├── openai_tts.py     OpenAI TTS implementation
    │   ├── pyttsx3_tts.py    Offline fallback (uses macOS `say` on macOS)
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

Personality system prompts live in `maid/ai/personalities.py` and can be edited directly to customize tone, vocabulary, or the threshold for when to stay silent.

---

## pyttsx3 voice options (macOS)

On macOS, pyttsx3 uses the built-in `say` command. You can select any installed system voice with `--voice` or by setting `macos_voice` in `config.toml`:

```
maid --tts pyttsx3 --voice "Bad News"
```

Run `say -v '?'` in Terminal to see all voices on your machine. The English (US) voices installed by default:

| Voice | Character |
|---|---|
| `Albert` | Classic robotic voice |
| `Bad News` | Deep, ominous tone |
| `Bahh` | Sheep-like |
| `Bells` | Bell tones |
| `Boing` | Bouncy cartoon voice |
| `Bubbles` | Bubbly, underwater feel |
| `Cellos` | Deep cello-like tone |
| `Eddy (English (US))` | Casual, natural-sounding male |
| `Flo (English (US))` | Natural-sounding female |
| `Fred` | Classic Mac voice |
| `Good News` | Upbeat, cheerful tone |
| `Grandma (English (US))` | Elderly female voice |
| `Grandpa (English (US))` | Elderly male voice |
| `Jester` | Playful, comedic |
| `Junior` | Young child voice |
| `Kathy` | Clear female voice |
| `Organ` | Pipe organ tones |
| `Ralph` | Gruff male voice |
| `Reed (English (US))` | Natural-sounding male |
| `Rocko (English (US))` | Deep, confident male |
| `Samantha` | Clear, default-quality female |
| `Sandy (English (US))` | Natural-sounding female |
| `Shelley (English (US))` | Natural-sounding female |
| `Superstar` | Reverb-heavy, dramatic |
| `Trinoids` | Alien robotic voice |
| `Whisper` | Soft, whispered voice |
| `Wobble` | Wobbly, unstable tone |
| `Zarvox` | Sci-fi robotic voice |

More voices (including high-quality neural voices like Ava and Tom) can be downloaded in **System Settings → Accessibility → Spoken Content → System Voice → Manage Voices**.

---

## Troubleshooting

**`Configuration error: anthropic_api_key is required`**
Add your key to `config.local.toml` under `[api]`, set the `ANTHROPIC_API_KEY` environment variable, or use `--mock` to run without it. If you're using Gemini, make sure `model` is set to a `gemini-*` model.

**`Configuration error: gemini_api_key is required`**
Get a free API key at https://aistudio.google.com/apikey and add it to `config.local.toml`. Make sure to generate the key from AI Studio specifically — keys from Google Cloud Console may not have free tier quota.

**`429 RESOURCE_EXHAUSTED` (Gemini)**
You've hit the free tier rate limit. MAID will automatically wait out the retry delay before continuing. To prevent it happening: increase `--interval` to 15s or more, or enable `--wait-for-tts`.

**`TTS initialization failed`**
If using ElevenLabs or OpenAI TTS, verify the API key is set. Fall back to `--tts pyttsx3` to confirm the rest of the pipeline works.

**No audio output**
On macOS, `afplay` is used to play OpenAI TTS audio — it ships with the OS. On Linux, install `mpg123` (`apt install mpg123`) or `ffmpeg`. pyttsx3 uses the system TTS engine directly (macOS `say`, Windows SAPI, Linux espeak).

**Screen capture is black or wrong monitor**
Run `maid --list-monitors` and confirm the `--monitor` index. On macOS, grant Screen Recording permission to Terminal in System Settings > Privacy & Security.

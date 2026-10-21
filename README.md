# Hands-free Mac for low vision

A voice-controlled assistant that lets a person with low vision use their Mac by
talking: hear email and text messages, reply to texts, start a show on Netflix,
Hulu, or Prime Video, check the weather, search the web, and find files. It runs
locally on Apple Silicon, and the same tools also work as a ChatGPT plugin.

Setup steps are in [SETUP.md](SETUP.md).

## Two ways to use it

| | ChatGPT plugin | Local voice assistant ("Brain") |
| --- | --- | --- |
| Understanding | Best | Good; depends on the model chosen |
| Voice | ChatGPT's voice | Kokoro (natural, local) |
| Cost | ChatGPT subscription | Free |
| Privacy | Requests go to ChatGPT | Everything stays on the Mac |
| Start | ChatGPT with the plugin enabled | `.venv/bin/python scripts/brain_voice.py` |

Both use the same tool code, so a fix in one place reaches both.

## What it can do

- **Mail** (Apple Mail): list the newest messages with inbox totals, read one, and
  draft a reply. It never sends email.
- **Texts** (Messages): list conversations with real unread counts, read a
  conversation, and send a reply after a spoken read-back and a "yes".
- **Contacts**: look up a person's phone numbers and email addresses.
- **TV**: start a show on Netflix, Hulu, or Prime Video in one step: choose the
  profile, search, open the title, press Resume or Play, and confirm a video is
  playing. It never presses Buy, Rent, Subscribe, or trial buttons.
- **Web** (Safari by default, or Chrome): search, read pages, and click links and
  buttons by their label.
- **Weather**: National Weather Service forecast for a home location (free, no key).
- **Files**: search like Spotlight (Command-Space), open, and read text files.
- **Speech**: read text aloud with pause, resume, and stop.

## Talking to Brain

| Say or do | What happens |
| --- | --- |
| Just talk | After "Brain start", no name is needed each time |
| "Brain, stop" | Cuts Brain off while it talks or works |
| "Brain stop" / "Brain start" | Pauses / resumes listening |
| "Brain, learn my voice" | Saves a voiceprint; other voices are then ignored |
| "Brain, shut down" | Quits |
| Control-Option-Command-B | Microphone fully off / on (Purr / Glass sounds) |

Sounds: *tink* means ready to listen; *pop* means heard you and working.

Brain ignores sounds that aren't speech (typing, clicks), discards Whisper's
repeated-phrase mistakes, and pauses itself after 5 quiet minutes. Headphones
make interrupting it much more reliable.

## Safety

- Texts are sent only after the recipient and exact words are read aloud and the
  user says "yes". This is enforced in code, not left to the model.
- Email is never sent; replies are saved as drafts.
- Streaming never buys, rents, or subscribes, and uses only approved profiles.
- Apple's Mail, Messages, and Contacts data are opened read-only.
- Email, text, web page, and file contents are treated as information, never as
  instructions to the assistant.
- Only `http` and `https` addresses can be opened.

## How it works

```
Microphone ─► Silero VAD (is it speech?) ─► voiceprint check ─► Whisper (MLX)
                                                                   │
Speaker ◄─ Kokoro ◄─ spoken-text cleanup ◄─ Qwen (mlx-lm) ◄─ tools (server.py)
```

| File in `scripts/` | Purpose |
| --- | --- |
| `server.py` | All tools, as an MCP server for ChatGPT and Codex |
| `brain.py` | Local model (Qwen via mlx-lm) using the same tools |
| `brain_voice.py` | Hands-free loop: listening, commands, interruptions |
| `mail.py`, `mail.js` | Apple Mail |
| `texts.py`, `messages.applescript` | Messages and Contacts |
| `browser.py`, `browser.js` | Safari/Chrome and streaming services |
| `weather.py` | National Weather Service forecast |
| `files.py` | Spotlight search, open, read |
| `speech.py` | Kokoro and macOS voices with playback controls |
| `common.py` | Shared helpers |
| `cli.py` | Command line for every tool (`--help`) |
| `toggle_brain_mic.sh` | Microphone on/off key |
| `start_chatgpt_voice.applescript` | Starts ChatGPT voice mode from Siri |

The ChatGPT plugin is **Low Vision — Mac assistance** (`low-vision-local`), in
`plugins/low-vision-mac/`. It starts `scripts/server.py` as a local stdio MCP
server: no web server, open port, or API key.

Local models (chosen at startup, downloaded on first use):

| Model | Suits |
| --- | --- |
| `Qwen/Qwen3-8B-MLX-6bit` (default) | 16 GB Macs |
| `mlx-community/Qwen3-8B-4bit` | Smaller, slightly faster |
| `mlx-community/Qwen3-30B-A3B-Instruct-2507-4bit` | 32 GB+ Macs, smarter |
| `mlx-community/Qwen3.6-35B-A3B-4bit` | 32 GB+ Macs, smartest |

## Command line

Every tool can be run from Terminal, which is handy for testing:

```sh
.venv/bin/python scripts/cli.py --help
.venv/bin/python scripts/cli.py mail-list --limit 5
.venv/bin/python scripts/cli.py texts --limit 5
.venv/bin/python scripts/cli.py watch hulu "High Potential"
.venv/bin/python scripts/cli.py weather
.venv/bin/python scripts/cli.py find-files "tax return" --name-only
echo "Hello there" | .venv/bin/python scripts/cli.py speak
```

## Tests

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tests/check_mcp.py
```

## Requirements

Apple Silicon Mac, Python 3.12, and Homebrew `portaudio`. Personal settings (name,
home town, weather location, streaming profiles) go in `.env`; see `.env.example`. Python packages are in
`requirements.txt` (ranges) and `requirements.lock.txt` (tested versions).
Permissions: Full Disk Access (texts, contacts), Automation (Mail, Messages,
browsers), Microphone, and "Allow JavaScript from Apple Events" in the browser.
See [SETUP.md](SETUP.md).

## Known limits

- Mac only; the local assistant needs Apple Silicon.
- Texts can only go to existing conversations.
- Streaming sites change their pages; the TV tool may need updating when they do.
- A bare "stop" can be drowned out by Brain's own voice; say "Brain, stop" or use
  headphones.
- Speech recognition and local models make mistakes. The ChatGPT plugin
  understands requests best.

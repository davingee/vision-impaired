# Setup: hands-free Mac for low vision

This guide sets up a voice assistant that lets someone with low vision use a Mac
by talking: email, texts, contacts, streaming TV, weather, the web, files, and
reading aloud. It works two ways, sharing the same tools:

- **ChatGPT plugin**: ChatGPT (or Codex) calls the tools. Best understanding.
- **Local voice assistant ("Brain")**: a local model (Qwen on MLX, Apple Silicon)
  listens and answers aloud. Free, private, and works without ChatGPT.

Requirements: an Apple Silicon Mac, macOS 14 or newer, and Homebrew.

## 1. Install the Python environment

From this project folder:

```sh
brew install portaudio uv
uv venv --python 3.12 .venv
CFLAGS="-I/opt/homebrew/include" LDFLAGS="-L/opt/homebrew/lib" \
  uv pip install --python .venv/bin/python -r requirements.lock.txt
```

`requirements.txt` lists the direct dependencies; `requirements.lock.txt` pins
the exact tested versions. The plugin expects the environment at `.venv`.

Check it:

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tests/check_mcp.py
```

## 2. Voices

The default voice is **Kokoro** (`kokoro:af_heart`), a natural-sounding voice
that runs locally for free. It downloads its model on first use. Other Kokoro
voices: `af_bella`, `af_nicole`, `am_michael`, `am_fenrir`, `bf_emma`,
`bm_george`. Choose one with `BRAIN_VOICE=kokoro:am_michael`.

Backup voice if Kokoro fails: System Settings › Accessibility › Spoken Content ›
System Voice › Manage Voices, then download **Ava (Premium)**.

## 3. Grant Mac permissions

System Settings › Privacy & Security. Grant these to the app that runs the
assistant (ChatGPT for the plugin; Terminal or VS Code for the local assistant):

| Permission | Needed for |
| --- | --- |
| **Full Disk Access** | Reading texts and contacts |
| **Automation** (prompted on first use) | Mail, Messages, Safari, Chrome |
| **Microphone** (prompted on first use) | Local voice assistant |
| **Accessibility** | Only the Siri shortcut for ChatGPT voice (step 6) |

Restart the app after changing Full Disk Access.

Reading and clicking web pages also needs one setting in each browser:

- Safari: Settings › Advanced › Show features for web developers, then
  Develop › **Allow JavaScript from Apple Events**
- Chrome: View › Developer › **Allow JavaScript from Apple Events** (may be
  locked if Chrome is managed by an organization; Safari is the default)

For TV, sign in to Netflix, Hulu, and Prime Video in Safari once.

## 4. Connect to ChatGPT (plugin)

1. Quit and reopen the ChatGPT desktop app.
2. Open Plugins and choose the local source **Low Vision — Mac assistance**.
3. Install **low-vision-mac** and start a new conversation with it enabled.
4. Ask: "Check this Mac," then "Read my latest email."

The plugin starts `scripts/server.py` with `.venv/bin/python`, using the full
paths in `plugins/low-vision-mac/.mcp.json`. If this folder moves, update those
paths and reinstall the plugin. After changing tools, restart ChatGPT.

## 5. Local voice assistant (optional)

Brain runs its language model with **MLX**, Apple's machine-learning library for
Apple Silicon (installed by step 1; no Ollama needed).

```sh
.venv/bin/python scripts/brain_voice.py
```

At startup it lists models; press Enter for the default or type a number:

| Model | Best for |
| --- | --- |
| `Qwen/Qwen3-8B-MLX-6bit` (default) | 16 GB Macs |
| `mlx-community/Qwen3-8B-4bit` | Smaller, slightly faster |
| `mlx-community/Qwen3-30B-A3B-Instruct-2507-4bit` | 32 GB+ Macs, smarter |
| `mlx-community/Qwen3.6-35B-A3B-4bit` | 32 GB+ Macs, smartest |

Brain starts `mlx_lm.server` on port 8765 itself. A model downloads on first use
(5–20 GB), and the Whisper speech model on the first run (about 1.6 GB). Skip the
question with `BRAIN_MODEL=<name>`. To use another OpenAI-compatible server
(LM Studio, Ollama), set `BRAIN_LLM_URL`.

The user's name, home town, and streaming profiles are set in Brain's
instructions in `scripts/brain.py` (`SYSTEM_PROMPT`) and in `scripts/browser.py`.

### Talking to Brain

- Once started, Brain listens to everything; no name needed each time.
- **"Brain stop"** pauses listening. **"Brain start"** resumes, as does any
  request starting with "Brain", like "Brain, read my latest email."
- After 5 quiet minutes Brain pauses on its own.
- While Brain is talking **or working** (searching, starting a show), say
  **"Brain, stop"** to cut it off; Brain says "Okay, stopped." A bare "stop" is
  often drowned out by Brain's own voice, so headphones help most. Control-C
  once, or the microphone key, also stops its talking.
- A soft *tink* means Brain is listening; a *pop* means it heard you and is working.
- Before sending a text, Brain reads it back; only "yes" sends it.
- **"Brain, shut down"** quits, or press Control-C.

### Teach Brain the user's voice

Brain ignores sounds that aren't a human voice (typing, clicks). To also ignore
other voices (TV, visitors), the user says **"Brain, learn my voice"**, or start
with `.venv/bin/python scripts/brain_voice.py --enroll`. After the chime they
talk normally for about 20 seconds. The voiceprint is saved at
`~/Library/Application Support/Brain/voiceprint.npy`; delete it to accept any voice.

Enroll the person who will use Brain, on their Mac. Anyone else's voiceprint
makes Brain ignore them.

Each request prints `(voice match 0.xx)`. If the user gets ignored, lower the
cutoff with `BRAIN_VOICE_MATCH=0.65`; if the TV gets through, raise it. Short
words like "yes" and "stop" are too brief to check, so they always pass.

### Microphone on/off key: Control-Option-Command-B

One press turns Brain's microphone fully off (and silences it); the next press
turns it back on. You hear Purr (off) or Glass (on), then Brain says
"Microphone off" / "Microphone on".

1. Shortcuts › new shortcut named **Brain Microphone**.
2. Add **Run Shell Script** and enter the full path to
   `scripts/toggle_brain_mic.sh` in this folder, for example
   `/Users/you/brain/scripts/toggle_brain_mic.sh`.
3. Click **ⓘ** (Shortcut Details) › **Add Keyboard Shortcut**, then press
   Control-Option-Command-B. (If that button is missing: turn on **Use as Quick
   Action** › **Services Menu**, then set the key in System Settings › Keyboard ›
   Keyboard Shortcuts › Services.)

No Accessibility permission is needed: the script creates or removes a flag file
that Brain watches. If Brain isn't running, the Mac says "Brain is not running."
No sound at all when pressing the keys means the Shortcut isn't set up.

### Typed testing without a microphone

```sh
.venv/bin/python scripts/brain.py
```

## 6. "Hey Siri" for ChatGPT voice (optional)

Starts ChatGPT's voice mode, bound to Control-Option-Command-V in ChatGPT settings.

1. Shortcuts › new shortcut with a distinctive name, such as **Voice Chat**.
   Avoid "ChatGPT" in the name; Siri may send that to its own ChatGPT feature.
2. Add **Run AppleScript** and paste the commands from
   `scripts/start_chatgpt_voice.applescript`.
3. Privacy & Security › Accessibility: add **Shortcuts** with **+** and turn it
   on. macOS may not prompt. The error "Shortcuts is not allowed to send
   keystrokes" means this step is missing.

Say "Hey Siri, Voice Chat." The same shortcut starts and stops voice mode.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "Cannot read chat.db" | Full Disk Access for the app running the assistant, then restart it |
| "Page control is off" | Browser setting in step 3 |
| "I lost my connection to my brain" | Restart `brain_voice.py`; it restarts the MLX server |
| Brain ignores speech | Say "Brain start"; check Microphone permission; check the voiceprint |
| Brain hears typing or TV as words | "Brain, learn my voice"; headphones; "Brain stop" |
| Microphone key does nothing | No sound means the Shortcut isn't set up (step 5) |
| Plugin tools missing in ChatGPT | Restart ChatGPT; reinstall the plugin |

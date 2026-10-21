# Setting up Bruce

Bruce gives an assistant hands on this Mac: Mail, Messages, Contacts, Safari,
Chrome, files, and speech. It runs in two ways that share the same tools:

- **ChatGPT plugin**: ChatGPT (or Codex) calls Bruce's tools. Best understanding.
- **Local voice assistant (Brain)**: talk to it and a local model (Qwen through
  MLX on Apple Silicon) answers aloud. Free, private, and works without ChatGPT.

Requirements: an Apple Silicon Mac, macOS 14 or newer, and Homebrew.

## 1. Install the Python environment

```sh
cd /Users/scott/code/bruce
brew install portaudio uv
uv venv --python 3.12 .venv
CFLAGS="-I/opt/homebrew/include" LDFLAGS="-L/opt/homebrew/lib" \
  uv pip install --python .venv/bin/python -r requirements.lock.txt
```

`requirements.txt` lists the four direct dependencies; `requirements.lock.txt`
pins the exact tested versions. The plugin expects the environment at `.venv`.

Check it:

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tests/check_mcp.py
```

## 2. Voices

The default voice is **Kokoro** (`kokoro:af_heart`), a natural-sounding voice
that runs locally for free. It downloads its model on first use. Other Kokoro
voices: `af_bella`, `af_nicole`, `am_michael`, `am_fenrir`, `bf_emma`,
`bm_george`. Choose one with `BRUCE_VOICE=kokoro:am_michael`.

Backup voice if Kokoro fails: System Settings › Accessibility › Spoken Content ›
System Voice › Manage Voices, then download **Ava (Premium)**.

## 3. Grant Mac permissions

System Settings › Privacy & Security. Grant these to the app that runs Bruce
(ChatGPT for the plugin; Terminal or VS Code for the local voice assistant):

| Permission | Needed for |
| --- | --- |
| **Full Disk Access** | Reading texts and contacts |
| **Automation** (prompted on first use) | Mail, Messages, Safari, Chrome |
| **Microphone** (prompted on first use) | Local voice assistant |
| **Accessibility** | Only the "Talk to Bruce" shortcut (step 6) |

Restart the app after changing Full Disk Access.

Browser page reading and clicking also need one setting in each browser:

- Chrome: View › Developer › **Allow JavaScript from Apple Events**
- Safari: Settings › Advanced › Show features for web developers, then
  Develop › **Allow JavaScript from Apple Events**

## 4. Connect to ChatGPT (plugin)

1. Quit and reopen the ChatGPT desktop app.
2. Open Plugins and choose the local source **Low Vision — Mac assistance**.
3. Install **low-vision-mac** and start a new conversation with it enabled.
4. Ask: "Use Bruce to check this Mac," then "Read my latest email."

The plugin starts `scripts/server.py` with `.venv/bin/python` (paths in
`plugins/low-vision-mac/.mcp.json`). If this folder moves, update those paths and
reinstall the plugin. After changing tools, restart ChatGPT.

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

Brain starts `mlx_lm.server` on port 8765 itself. A model downloads on first
use (5–20 GB). Skip the question with `BRUCE_MODEL=<name>`. To use another
OpenAI-compatible server (LM Studio, Ollama), set `BRUCE_LLM_URL`.

The first run downloads the Whisper speech model (about 1.6 GB). The local
assistant is called **Brain**; it talks to Bruce.

- Once started, Brain listens to everything; no name needed each time.
- **"Brain stop"** pauses listening. **"Brain start"** resumes, as does any
  request starting with "Brain", like "Brain, read my latest email."
- After 5 quiet minutes Brain pauses on its own.
- While Brain is talking **or working** (searching, starting a show), say
  **"Brain, stop"** to cut it off; Brain says "Okay, stopped." A bare "stop" is
  often drowned out by Brain's own voice. Headphones help most. Control-C once,
  or the microphone key, also stops its talking. Headphones make this more reliable.
- A soft *tink* means Brain is listening; a *pop* means it heard you and is working.
- Before sending a text, Brain reads it back; only "yes" sends it.
- **"Brain, shut down"** quits, or press Control-C.

### Teach Brain Bruce's voice

Brain ignores sounds that aren't a human voice (typing, clicks). To also ignore
other voices (TV, visitors), have Bruce say **"Brain, learn my voice"**, or start
with `.venv/bin/python scripts/brain_voice.py --enroll`. After the chime he talks
normally for about 20 seconds. The voiceprint is saved at
`~/Library/Application Support/Bruce/voiceprint.npy`; delete it to accept any voice.

Each request prints `(voice match 0.xx)`. If Bruce gets ignored, lower the cutoff
with `BRUCE_VOICE_MATCH=0.65`; if the TV gets through, raise it. Short words like
"yes" and "stop" are too brief to check, so they always pass.

### Microphone on/off key: Control-Option-Command-B

One press turns Brain's microphone fully off (and silences it); the next press
turns it back on. Brain says "Microphone off" / "Microphone on".

1. Shortcuts › new shortcut named **Brain Microphone**.
2. Add **Run Shell Script** and enter:
   `/Users/scott/code/bruce/scripts/toggle_brain_mic.sh`
3. Click the **ⓘ** (Shortcut Details) › **Add Keyboard Shortcut**, then press
   Control-Option-Command-B.

No Accessibility permission is needed; the script only signals `brain_voice.py`.
If Brain isn't running, the Mac says "Brain is not running."

Typed testing without a microphone:

```sh
.venv/bin/python scripts/brain.py
```



## 6. "Hey Siri, Talk to Bruce" (ChatGPT voice)

Starts ChatGPT's voice mode, bound to Control-Option-Command-V in ChatGPT settings.

1. Shortcuts › new shortcut named **Talk to Bruce**.
2. Add **Run AppleScript** and paste the commands from
   `scripts/start_chatgpt_voice.applescript`.
3. Privacy & Security › Accessibility: add **Shortcuts** with **+** and turn it
   on. macOS may not prompt. The error "Shortcuts is not allowed to send
   keystrokes" means this step is missing.

The same shortcut starts and stops voice mode.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "Cannot read chat.db" | Full Disk Access for the app running Bruce, then restart it |
| "Page access is turned off" | Browser setting in step 3 |
| "I lost my connection to my brain" | Restart `brain_voice.py`; it restarts the MLX server |
| Brain ignores speech | Say "Brain start"; check Microphone permission |
| Plugin tools missing in ChatGPT | Restart ChatGPT; reinstall the plugin |

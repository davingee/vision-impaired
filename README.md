# Bruce — accessible Mac scripts

Setup: see [SETUP.md](SETUP.md).

Local scripts for Dad to use Apple Mail, read text documents, and hear spoken
output through ChatGPT or Codex.

## What's ready

- Python environment installed in `.venv`, with MCP 1.30.0 and its dependencies.
- Apple Mail: list recent inbox messages, read an exact message or the selection,
  and prepare a reply draft. **No email-sending tool.**
- Messages: list recent conversations with unread counts, read a conversation,
  and send a text to an existing conversation after spoken confirmation.
- Contacts: search the address book by name for phones and emails.
- Read UTF-8 text, Markdown, CSV, and log files.
- Safari and Chrome: open a web address, list tabs, read the front page, and
  click a link or button by its label (for Hulu: show, episode, Play).
- Weather: National Weather Service forecast for Helena, MT (free, no key).
- Web search: Google results returned as text.
- Files: search like Command-Space (Spotlight), open a file, read text files.
- Open Mail, Messages, Contacts, Safari, Chrome, or Finder.

Code layout in `scripts/`:

| File | Area |
| --- | --- |
| `mail.py`, `mail.js` | Apple Mail |
| `texts.py`, `messages.applescript` | Messages and Contacts |
| `browser.py`, `browser.js` | Safari and Chrome |
| `files.py` | Spotlight search, open, read |
| `weather.py` | NWS forecast (api.weather.gov) |
| `speech.py` | Ava speech with pause/resume/stop |
| `common.py` | Shared command and JXA helpers |
| `bruce.py` | Command line (`--help`) |
| `server.py` | MCP tools for ChatGPT/Codex |
| `brain.py` | Local Qwen (MLX) using the same tools |
| `brain_voice.py` | Hands-free: wake word, local Whisper, Ava |
- Speak locally using **Ava (Premium)** at 175 words per minute.
- MCP tools to pause, resume, stop, and inspect Bruce's speech.
- A local plugin and repository marketplace, ready for installation in a
  compatible ChatGPT desktop client.

Ava Premium was downloaded through Apple's System Settings. No cloud speech
account, API key, or recurring speech charge is needed for this local voice.
The scripts explicitly select Ava; the Mac's global system voice was not changed.

## Use in this Codex folder now

Open `/Users/scott/code/bruce` as the working folder. `AGENTS.md` tells the
assistant how to use the scripts. You can ask:

- “Read my latest email aloud using the Bruce scripts.”
- “Read this text file aloud.”
- “Prepare a reply to that email saying …”
- “Read my latest texts.” / “Text Mom back saying I'll call tonight.”

The assistant can run the scripts directly using its local execution tools.
An ordinary chat without local tools does not gain Mac access just by uploading
these Python files.

## Connect the tools to ChatGPT desktop

Compatibility fix (version 0.1.1): the installed host recognized the plugin
listing but returned no MCP servers for the portable root manifest. Bruce now
uses `.codex-plugin/plugin.json` and `.mcp.json`, matching this host's working
plugins. The portable manifest is retained as `plugin.portable.json` for reference,
not as an active manifest. Do not rename it back without testing host discovery.
After reinstalling, `plugin/read` reports the `bruce` MCP server, and the direct
MCP test still discovers 12 tools. Voice-session access remains to be tested.

The local plugin catalog is `.agents/plugins/marketplace.json`. The plugin is
under `plugins/bruce/`. It starts a local **stdio MCP server**: no web server,
public tunnel, API key, or open network port.

In a desktop client that supports local plugin marketplaces:

1. Keep this folder available as the local project and restart the ChatGPT desktop
   app after saving your work.
2. Open the Plugins Directory and choose the local source
   **Bruce — Mac assistance** (`bruce-local`).
3. Install **bruce** and start a new local conversation with it enabled.
4. Ask “Use Bruce to check this Mac,” then “Use Bruce to say hello.”
5. Test “Read my latest email” and the speech pause/resume/stop commands.

The assistant can help perform these steps. A restart was not forced while this
conversation was active. Installation through ChatGPT and voice-mode tool
availability have **not yet been verified** in this account.

Local marketplace support varies by client. If this catalog is not visible,
inspect the installed app and its plugin settings rather than assuming that a
web chat can run a local script. The official remote-MCP alternative involves a
separate connection setup; it is not configured here.

The plugin launch paths are specific to this Mac:

```text
/Users/scott/code/bruce/.venv/bin/python
/Users/scott/code/bruce/scripts/server.py
```

If this folder moves, update `plugins/bruce/mcp.json`. The plugin is a local
development package referencing this workspace; it is not a portable download.
After changing plugin configuration, refresh/reinstall the local plugin as
needed because ChatGPT may use a cached copy.

## Commands for development

Run from this folder:

```sh
.venv/bin/python scripts/bruce.py doctor
.venv/bin/python scripts/bruce.py voices
.venv/bin/python scripts/bruce.py mail-list --limit 5
.venv/bin/python scripts/bruce.py mail-read --id 123
.venv/bin/python scripts/bruce.py mail-read
.venv/bin/python scripts/bruce.py read-file /absolute/path/document.txt
.venv/bin/python scripts/bruce.py speak --file /absolute/path/document.txt
.venv/bin/python scripts/bruce.py open-app Mail
.venv/bin/python scripts/bruce.py mail-draft --id 123 --file /absolute/path/reply.txt
```

Replace `123` with a real ID returned by `mail-list`. Without an ID, `mail-read`
requires exactly one selected message. ID-based lookup currently covers only
the combined inbox. Listing uses received dates, newest first.

The CLI speech command waits for completion and can be stopped with Control-C.
MCP speech starts in the background so separate pause/resume/stop tools can work.
Those controls affect only speech owned by the same server process.
Long messages may need to be split into chunks by the assistant.

## Messages and Contacts

Messages' AppleScript dictionary can send but cannot read message text, so
reading uses `~/Library/Messages/chat.db` and contacts use the AddressBook
databases, both opened read-only. The app running Bruce (ChatGPT, Codex, or
Terminal) needs **Full Disk Access** in Privacy & Security.

Sending uses `scripts/messages.applescript` and requires `user_confirmed=true`
(CLI: `--yes`), which the assistant sets only after reading the recipient and
exact text back and hearing yes. Afterward Bruce checks the database and reports
`sent`, `failed`, or `pending`. Only existing conversations can receive texts;
start a brand-new one in Messages first.

```sh
.venv/bin/python scripts/bruce.py contacts "jane"
.venv/bin/python scripts/bruce.py texts --limit 5
.venv/bin/python scripts/bruce.py text-read 123
.venv/bin/python scripts/bruce.py text-send 123 --file reply.txt --yes
```

Newer macOS stores text in an encoded `attributedBody` field. Bruce decodes it
with a small heuristic (3,000 of 3,000 recent messages decoded here); an Apple
format change could break it.

## Web pages

Reading and clicking pages needs a one-time browser setting:

- Chrome: View › Developer › **Allow JavaScript from Apple Events**.
- Safari: Settings › Advanced › Show features for web developers, then
  Develop › **Allow JavaScript from Apple Events**.

Opening addresses and listing tabs work without it. Clicks match visible labels;
sites change their layouts, so Hulu navigation is best-effort and unverified.

## Start ChatGPT voice with Siri

ChatGPT's voice button is bound to Control-Option-Command-V in ChatGPT settings.
[scripts/start_chatgpt_voice.applescript](scripts/start_chatgpt_voice.applescript)
brings ChatGPT forward and presses that shortcut.

1. In Shortcuts, create a shortcut named **Talk to Bruce**.
2. Add a **Run AppleScript** action and paste the script's three command lines.
   Dragging the `.applescript` file in only adds a File action; it does not run it.
3. In System Settings › Privacy & Security › Accessibility, add Shortcuts with
   **+** (macOS may not prompt) and switch it on. Quit and reopen Shortcuts.
   Error "Shortcuts is not allowed to send keystrokes" means this step is missing.
4. Say "Hey Siri, Talk to Bruce."

Avoid "ChatGPT" in the shortcut name; Siri may route that to its built-in
ChatGPT feature. Verified from the Shortcuts Run button. If ChatGPT is closed
and voice does not start, raise the delay to 2 seconds.

## Voice quality

Preference: use ChatGPT's built-in voice for conversation and free local speech
for reading when needed. Do not add a paid TTS API. Avoid simultaneous ChatGPT
and Ava speech.

ChatGPT Voice supports interrupting an answer by speaking. Asking “stop” or
“wait” can interrupt, and “continue” requests continuation, but this is not a
verified exact-position audio pause/resume feature. Bruce's pause/resume tools
control only its own Ava playback; they cannot pause ChatGPT's native audio.
ChatGPT Voice availability and usage limits depend on the account.
See [ChatGPT Voice](https://learn.chatgpt.com/docs/features/voice).

**Ava Premium** is our starting local voice, not a claim that one voice is
objectively best for everyone. Try a sample and adjust the voice and speed to
Dad's preference. Use `voices` to see installed alternatives.

For a cloud upgrade, OpenAI recommends `marin` or `cedar` with
`gpt-4o-mini-tts` for best quality in its TTS offering. That would send the text
to OpenAI and require an API setup with usage charges. Cloud speech is not
implemented or configured here. ChatGPT's conversational voice and these local
script voices are separate systems.

All speech generated by these scripts is synthetic.

## Libraries and reinstalling

Full setup steps are in [SETUP.md](SETUP.md).

| Component | Use |
| --- | --- |
| `mcp` | Plugin tools for ChatGPT/Codex (`scripts/server.py`) |
| `SpeechRecognition` + `PyAudio` | Microphone capture for the local voice assistant |
| `mlx-whisper` | Local speech-to-text on Apple Silicon |
| `mlx-lm` + Qwen3 (MLX) | Local model for `scripts/brain.py` |
| macOS `osascript`, `say`, `open`, `mdfind` | Mac app control, speech, Spotlight |

`requirements.txt` gives direct dependency ranges; `requirements.lock.txt` pins
the tested environment (Python 3.12).

## Verification and limits

Verified on this Mac:

- Python 3.14.7 and required macOS commands.
- Mail account access, recent message listing, and body retrieval by exact ID.
- Four unit tests covering input validation, text truncation, data transport,
  and avoiding signals to an exited speech process.
- A real MCP client/server handshake and tool calls.
- Ava Premium present in `say` and a spoken sample completing with exit code 0.

Audio audibility still requires listener confirmation. A successful process
is not proof of sound through the intended speaker.

Reply-draft creation is implemented but has not been exercised against a real
message, to avoid creating an unsolicited draft. No email was sent.
Hulu episode navigation, PDF/Word extraction, and microphone transcription are
not implemented. The scripts complement a voice-capable assistant; they do not
themselves provide a continuously listening voice interface.

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/check_mcp.py
```

Mac Automation permissions depend on which app launches the scripts. Existing
permission worked in this session; another host may trigger a permission prompt.

## Accessibility and data handling

Keep responses short, ask one question at a time, and perform computer actions
instead of requiring small-control navigation. Background media and pauses are
not commands. Distinguish opening, reading, playing, and hearing.

Private text is passed as data, not inserted into executable code. The local
scripts do not upload content, though information returned to ChatGPT is part
of that conversation. Mail and file tools do not retain content logs. The
assistant should read only files and messages relevant to the user's request.

## Sources

- [OpenAI: local plugin packaging and marketplaces](https://developers.openai.com/plugins/build/plugins)
- [OpenAI: connect and test plugins](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [OpenAI: speech models and voice recommendations](https://developers.openai.com/api/docs/guides/text-to-speech)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [Evaluated chatgptmac source](https://github.com/soupsoftware/chatgptmac/blob/master/chatgptmac.py)

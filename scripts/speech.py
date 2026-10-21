"""Local speech, with pause/resume/stop. Kokoro (natural, local) by default; macOS say as backup."""
import logging
import os
import signal
import subprocess
import sys
import tempfile
import threading
import warnings
import wave
from contextlib import redirect_stdout

from common import run_command

DEFAULT_VOICE = os.environ.get("BRUCE_VOICE", "kokoro:af_heart")
FALLBACK_VOICE = "Ava (Premium)"
KOKORO_MODEL = "mlx-community/Kokoro-82M-bf16"
# A few of Kokoro's English voices: a = American, b = British; f = female, m = male.
KOKORO_VOICES = ["af_heart", "af_bella", "af_nicole", "am_michael", "am_fenrir",
                 "bf_emma", "bm_george"]
_kokoro = None
# Kokoro's helpers log pronunciation and download chatter; Bruce's console needs none of it.
for noisy in ("httpx", "huggingface_hub", "misaki"):
    logging.getLogger(noisy).setLevel(logging.ERROR)
# phonemizer resets its own level on every use; disabling sticks. Its "words count
# mismatch" warning only means espeak split a word like "$PATH" differently.
logging.getLogger("phonemizer").disabled = True


def voices():
    say_voices = run_command(["/usr/bin/say", "-v", "?"]).splitlines()
    return [f"kokoro:{name}" for name in KOKORO_VOICES] + say_voices


def kokoro_wav(text, voice, rate):
    """Synthesize to a private temporary WAV file, deleted when closed."""
    global _kokoro
    import numpy as np
    from mlx_audio.tts.utils import load_model
    speed = min(max(rate / 175, 0.5), 2.0)
    # Kokoro prints progress to stdout; the MCP server needs stdout for ChatGPT.
    with redirect_stdout(sys.stderr), warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)  # torch.jit.script notice
        if _kokoro is None:
            _kokoro = load_model(KOKORO_MODEL)
        audio = np.concatenate([np.array(part.audio) for part in _kokoro.generate(
            text=text, voice=voice, speed=speed, lang_code=voice[0])])
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    file = tempfile.NamedTemporaryFile(suffix=".wav")
    with wave.open(file.name, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        out.writeframes(pcm.tobytes())
    return file


class Speech:
    """Own the process so controls cannot accidentally stop another app's audio."""

    def __init__(self):
        self.process = None
        self.source = None
        self.paused = False
        self.lock = threading.RLock()

    def _cleanup(self):
        if self.source:
            self.source.close()
            self.source = None

    def start(self, text, voice=DEFAULT_VOICE, rate=175):
        if not text.strip() or len(text) > 100000:
            raise ValueError("Provide between 1 and 100,000 characters.")
        if not 80 <= rate <= 400:
            raise ValueError("Speech rate must be 80–400 words per minute.")
        names = [line.split(" #", 1)[0].rsplit(None, 1)[0].strip() for line in voices()]
        if voice not in names:
            raise ValueError("Voice is unavailable. Use list_voices first.")
        with self.lock:
            self.stop()
            if voice.startswith("kokoro:"):
                try:
                    self.source = kokoro_wav(text, voice.removeprefix("kokoro:"), rate)
                    command = ["/usr/bin/afplay", self.source.name]
                except Exception as exc:  # Never leave Bruce in silence.
                    print(f"Kokoro failed ({exc}); using {FALLBACK_VOICE}.", file=sys.stderr)
                    voice = FALLBACK_VOICE
            if not voice.startswith("kokoro:"):
                # An anonymous file avoids putting private text in process arguments.
                self.source = tempfile.TemporaryFile(mode="w+t")
                self.source.write(text)
                self.source.seek(0)
                command = ["/usr/bin/say", "-v", voice, "-r", str(rate)]
            self.process = subprocess.Popen(
                command, stdin=self.source if command[0] == "/usr/bin/say" else None,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                code = self.process.wait(timeout=0.15)
            except subprocess.TimeoutExpired:
                code = None
            if code not in (None, 0):
                self._cleanup()
                raise RuntimeError("macOS speech failed to start.")
            return {"status": "started" if code is None else "finished",
                    "voice": voice, "audible": "unverified"}

    def status(self):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self._cleanup()
                return {"status": "idle"}
            return {"status": "paused" if self.paused else "speaking"}

    def pause(self):
        with self.lock:
            if self.status()["status"] == "speaking":
                self.process.send_signal(signal.SIGSTOP)
                self.paused = True
            return self.status()

    def resume(self):
        with self.lock:
            if self.status()["status"] == "paused":
                self.process.send_signal(signal.SIGCONT)
                self.paused = False
            return self.status()

    def stop(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                if self.paused:
                    self.process.send_signal(signal.SIGCONT)
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.paused = False
            self._cleanup()
            return {"status": "stopped"}

"""Hands-free Brain for Bruce. Once started, Brain listens without needing its name.

"Brain stop" pauses listening; "Brain start" (or "Brain, <request>") resumes.
While Brain is talking or working, "Brain, stop" cuts it off (a bare "stop" is often
drowned out by Brain's own voice).
"Brain, shut down" quits. After 5 quiet minutes Brain pauses on its own.
Control-Option-Command-B (Shortcut running toggle_brain_mic.sh) turns the mic fully off and on.
"Brain, learn my voice" (or --enroll) saves a voiceprint; other voices are then ignored.
Local Whisper hears, local Qwen (MLX) thinks, Kokoro speaks. Audio stays on the Mac.
Run: .venv/bin/python scripts/brain_voice.py
"""

from dotenv import load_dotenv

load_dotenv()  # For BRAIN_MODEL, BRAIN_VOICE, and BRAIN_LLM_URL.

import os
import re
import sys
import subprocess
import threading
import time
import warnings
import zlib
from pathlib import Path

# Library notices about their own future changes; nothing for Bruce to act on.
warnings.filterwarnings("ignore", message=r".*torch\.jit\.(load|script).*is deprecated")
warnings.filterwarnings("ignore", message=r".*pkg_resources is deprecated")

import brain as brain_module
import mlx_whisper
import numpy as np
import speech_recognition as sr
from brain import LLM_URL, Brain
from common import CANCEL
from speech import DEFAULT_VOICE, Speech

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
# Whisper sometimes hears "Brain" as "Brian" or "Brane".
WAKE = re.compile(
    r"^\W*(?:(?:hey|hi|ok|okay)\W+)?(?:brain|brian|brane|brayn)\b\W*", re.IGNORECASE
)
START = re.compile(r"^(?:start|wake up|listen|i'?m back)\b", re.IGNORECASE)
SLEEP = re.compile(
    r"^(?:stop|stop listening|sleep|go to sleep|pause)\W*$", re.IGNORECASE
)
QUIT = re.compile(r"\b(?:shut ?down|turn off|goodbye)\b", re.IGNORECASE)
YES = re.compile(
    r"^\W*(?:yes|yeah|yep|yup|sure|send it|go ahead|please do)\b", re.IGNORECASE
)
# Whisper invents these from silence or background noise.
NOISE = {"", "you", "thank you", "thanks for watching", "bye", "okay"}
IDLE_PAUSE_SECONDS = 300
# Words Whisper should expect; helps it spell names and commands right.
VOCABULARY = "Brain, Bruce, Scott, Netflix, email, texts, Safari, Blacklist."
READY_SOUND = "/System/Library/Sounds/Tink.aiff"  # Brain is listening.
HEARD_SOUND = "/System/Library/Sounds/Pop.aiff"  # Brain heard you and is working.

speech = Speech()


# Said while Brain is talking, these cut it off.
STOP_TALKING = re.compile(r"\b(?:stop|quiet|enough|shut up|hold on|wait)\b", re.IGNORECASE)


def interrupted(heard, spoken):
    """True if Bruce said a stop word. The mic also hears Brain itself, so a stop word
    that is in Brain's own sentence does not count."""
    return any(m.group(0).lower() not in spoken.lower() for m in STOP_TALKING.finditer(heard))


def say(text, hear=None):
    """Speak. With hear(), keep listening so Bruce can say "stop"; Control-C also stops it."""
    print(f"[Brain] {text}")
    speech.start(text)
    try:
        if hear is None:
            speech.process.wait()
            return False
        while speech.process.poll() is None:
            heard = hear()
            if heard and interrupted(heard, text):
                print(f"[Bruce] {heard}  (stopped Brain)")
                speech.stop()
                return True
        return False
    except KeyboardInterrupt:
        speech.stop()
        print("(stopped Brain)")
        return True


def chime(sound):
    """Bruce can't see the screen; sounds tell him when to talk and when Brain heard."""
    subprocess.Popen(["/usr/bin/afplay", sound])


# Bruce's voiceprint: personal, so it lives outside the project folder.
VOICEPRINT = Path.home() / "Library/Application Support/Brain/voiceprint.npy"
# How alike a voice must be to Bruce's (0-1). Tune if he is ignored (lower it) or the
# TV gets through (raise it); each request prints its score.
VOICE_MATCH = float(os.environ.get("BRAIN_VOICE_MATCH", "0.72"))
LEARN = re.compile(r"^(?:learn|remember|know) my voice", re.IGNORECASE)
_vad, _encoder = None, None


def to_samples(audio):
    raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def speech_seconds(samples):
    """Seconds of human speech per Silero VAD; typing, clicks, and hum count as zero."""
    global _vad
    import torch
    from silero_vad import get_speech_timestamps, load_silero_vad
    if _vad is None:
        _vad = load_silero_vad()
    stamps = get_speech_timestamps(torch.from_numpy(samples), _vad, sampling_rate=16000)
    return sum(stamp["end"] - stamp["start"] for stamp in stamps) / 16000


def voice_embedding(samples):
    global _encoder
    from resemblyzer import VoiceEncoder
    if _encoder is None:
        _encoder = VoiceEncoder("cpu", verbose=False)
    return _encoder.embed_utterance(samples)


def is_known_voice(samples, speech):
    """True unless a voiceprint exists and this clearly is someone else. Under a second
    of speech ("yes", "stop") is too short to judge, so it passes."""
    if not VOICEPRINT.exists() or speech < 1.0:
        return True
    score = float(np.dot(voice_embedding(samples), np.load(VOICEPRINT)))
    print(f"  (voice match {score:.2f})")
    return score >= VOICE_MATCH


# While Brain talks, Whisper favors Brain's long sentence over a short interruption.
# Expecting stop words catches "Brain, stop" over speech (bare "stop" is often missed).
STOP_PROMPT = "Stop. Wait. Enough. Brain, stop."


def transcribe(audio, check_voice=True, prompt=VOCABULARY):
    """check_voice=False while Brain talks: the clip is mostly Brain's own voice, so a
    voiceprint check would throw away Bruce's "stop" along with it."""
    samples = to_samples(audio)
    speech = speech_seconds(samples)
    if speech < 0.3:
        return ""  # Not a voice: typing, a door, the dishwasher.
    if check_voice and not is_known_voice(samples, speech):
        print("  (ignored: not Bruce's voice)")
        return ""
    result = mlx_whisper.transcribe(
        samples, path_or_hf_repo=WHISPER_MODEL, language="en", initial_prompt=prompt,
        condition_on_previous_text=False,  # Stops one misheard phrase feeding the next.
    )
    # Drop segments Whisper itself thinks are not speech (TV hum, music, room noise).
    text = " ".join(seg["text"].strip() for seg in result.get("segments", [])
                    if not (seg.get("no_speech_prob", 0) > 0.6 and seg.get("avg_logprob", 0) < -1))
    return "" if hallucinated(text) else text.strip()


def hallucinated(text):
    """Whisper sometimes loops one phrase on noise ("I have a really good one, I have a
    really good one, ..."). Real speech is rarely this repetitive."""
    if len(text) < 40:
        return False
    if len(text) / len(zlib.compress(text.encode())) > 2.4:  # Whisper's own repetition test.
        return True
    words = re.findall(r"[a-z']+", text.lower())
    phrases = [" ".join(words[i:i + 4]) for i in range(len(words) - 3)]
    return bool(phrases) and max(phrases.count(x) for x in set(phrases)) >= 3


def enroll(recognizer, source, seconds=20):
    """Learn Bruce's voice from about 20 seconds of him talking naturally."""
    say("Let's learn your voice. After the chime, talk normally for about twenty "
        "seconds. Tell me about your day, or anything at all.")
    chime(READY_SOUND)
    time.sleep(0.5)
    samples = to_samples(recognizer.record(source, duration=seconds))
    if speech_seconds(samples) < 8:
        say("I didn't hear enough talking. Say Brain, learn my voice, to try again.")
        return False
    VOICEPRINT.parent.mkdir(parents=True, exist_ok=True)
    np.save(VOICEPRINT, voice_embedding(samples))
    say("Got it. I'll listen for your voice now.")
    return True


def route(heard, active):
    """Return (command, request); command is None, "start", "sleep", "quit", "learn",
    or "ask"."""
    match = WAKE.match(heard)
    rest = heard[match.end() :].strip() if match else heard.strip()
    if match and LEARN.match(rest):
        return "learn", ""
    if match:
        if QUIT.search(rest):
            return "quit", ""
        if SLEEP.match(rest):
            return "sleep", ""
        if not rest or START.match(rest):
            return "start", ""
        return "ask", rest
    if not active or rest.lower().strip(" .!?,") in NOISE:
        return None, ""
    return "ask", rest


def ask_while_listening(brain, request, hear):
    """Run the request in the background while listening, so "stop" cancels it.
    Returns the answer, or None if stopped."""
    CANCEL.clear()
    result = {}

    def work():
        try:
            result["answer"] = brain.ask(request)
        except RuntimeError as exc:
            result["answer"] = str(exc)

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    while worker.is_alive() and not CANCEL.is_set():
        heard = hear()
        if heard and STOP_TALKING.search(heard):
            print(f"[Bruce] {heard}  (stopped the task)")
            CANCEL.set()
    worker.join(timeout=30)  # Tools stop at their next step; a model reply is discarded.
    return None if CANCEL.is_set() else result.get("answer")


# Control-Option-Command-B runs scripts/toggle_brain_mic.sh, which creates or
# deletes this file (and plays the sound). A file, not a signal: it works no matter
# what Brain is busy with.
MIC_OFF_FLAG = Path.home() / "Library/Application Support/Brain/mic_off"


class MicSwitch:
    """The microphone is on unless the hotkey's flag file exists."""

    def is_set(self):
        return not MIC_OFF_FLAG.exists()

    def set(self):
        MIC_OFF_FLAG.unlink(missing_ok=True)

    def clear(self):
        MIC_OFF_FLAG.parent.mkdir(parents=True, exist_ok=True)
        MIC_OFF_FLAG.touch()


mic_on = MicSwitch()


def watch_switch(poll=0.1):
    """Background thread: the moment the mic is switched off, go silent and cancel any
    task, whatever the main loop is doing."""
    was_on = True
    while True:
        on = mic_on.is_set()
        if was_on and not on:
            CANCEL.set()
            speech.stop()
        was_on = on
        time.sleep(poll)


class MicOff(Exception):
    pass


def stop_reads_when_off(source):
    """Make every microphone read fail once the hotkey turns the mic off. Otherwise a
    noisy room keeps one listen() going for up to 30 seconds before anyone checks."""
    read = source.stream.read

    def guarded(size):
        if not mic_on.is_set():
            raise MicOff()
        return read(size)

    source.stream.read = guarded


def wait_until_mic_on():
    while not mic_on.is_set():
        time.sleep(0.2)


def main():
    mic_on.set()  # Start listening, even if Brain last quit with the mic off.
    threading.Thread(target=watch_switch, daemon=True).start()
    brain_module.choose_model()
    print(f"Model: {brain_module.MODEL} at {LLM_URL} | Voice: {DEFAULT_VOICE} | Hearing: {WHISPER_MODEL}")
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.8  # Room for Bruce to pause mid-sentence.
    mic = {}

    def listen(timeout=None, limit=30, check_voice=True, prompt=VOCABULARY):
        try:
            audio = recognizer.listen(mic["source"], timeout=timeout, phrase_time_limit=limit)
        except (sr.WaitTimeoutError, MicOff):
            return ""
        return transcribe(audio, check_voice, prompt)

    def hear_while_talking():
        # Short, so a "stop" is noticed within seconds. Only stop words count here.
        return listen(timeout=1, limit=3, check_voice=False, prompt=STOP_PROMPT)

    def confirm(question):
        say(question + " Say yes or no.")
        answer = listen(timeout=10)
        print(f"[Bruce] {answer}")
        return bool(YES.match(answer))

    brain = Brain(confirm)
    calibrated = False
    active, last_request = True, time.time()
    while True:
        if not mic_on.is_set():
            say("Microphone off.")
            wait_until_mic_on()
            say("Microphone on.")
            active, last_request = True, time.time()
        with sr.Microphone(sample_rate=16000) as source:
            mic["source"] = source
            stop_reads_when_off(source)
            if not calibrated:
                print("Measuring room noise; stay quiet for a moment.")
                recognizer.adjust_for_ambient_noise(source, duration=1.5)
                # A rising threshold mistakes quiet sentence endings for silence.
                recognizer.dynamic_energy_threshold = False
                calibrated = True
                if "--enroll" in sys.argv or not VOICEPRINT.exists():
                    if "--enroll" in sys.argv:
                        enroll(recognizer, source)
                    else:
                        print("No voiceprint yet: any voice is accepted. "
                              "Say 'Brain, learn my voice' or start with --enroll.")
                say("Brain is listening. To interrupt me, say Brain, stop.")
            chime(READY_SOUND)
            while mic_on.is_set():
                heard = listen(timeout=2)  # Short, so the hotkey takes effect quickly.
                if not mic_on.is_set():
                    break
                if active and time.time() - last_request > IDLE_PAUSE_SECONDS:
                    active = False
                    say("I'll rest now. Say Brain start when you need me.")
                command, request = route(heard, active)
                if command is None:
                    continue  # Background talk, TV, or silence.
                print(f"[Bruce] {heard}")
                chime(HEARD_SOUND)
                last_request = time.time()
                if command == "quit":
                    say("Goodbye, Bruce.")
                    return
                if command == "learn":
                    enroll(recognizer, source)
                    chime(READY_SOUND)
                    continue
                if command == "sleep":
                    active = False
                    say("Okay, I'll stop listening. Say Brain start when you need me.")
                    continue
                active = True
                if command == "start":
                    say("I'm listening.")
                    chime(READY_SOUND)
                    continue
                answer = ask_while_listening(brain, request, hear_while_talking)
                if answer is None:  # Bruce said stop.
                    if mic_on.is_set():
                        say("Okay, stopped.")
                        chime(READY_SOUND)
                    last_request = time.time()
                    continue
                if mic_on.is_set():  # Turned off while thinking: stay silent.
                    say(answer, hear=hear_while_talking)
                    chime(READY_SOUND)
                last_request = time.time()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        speech.stop()

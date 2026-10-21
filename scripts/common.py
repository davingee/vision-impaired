"""Shared helpers: run commands, pass JSON to JXA scripts, open apps."""
import json
import platform
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Set when Bruce says "stop" mid-task; long tools check it between steps.
CANCEL = threading.Event()


class Cancelled(Exception):
    pass


def checkpoint():
    if CANCEL.is_set():
        raise Cancelled("Stopped at Bruce's request.")


def run_command(args, *, text=None, timeout=30):
    result = subprocess.run(args, input=text, capture_output=True, text=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"Command failed: {args[0]}")
    return result.stdout.strip()


def jxa(script, request, timeout=45):
    # Arguments travel as JSON data, never as executable JavaScript.
    # A private temporary file keeps private text out of the process command line.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as payload:
        json.dump(request, payload)
        payload.flush()
        raw = run_command(["/usr/bin/osascript", "-l", "JavaScript",
                           str(ROOT / script), payload.name], timeout=timeout)
    return json.loads(raw)


def doctor():
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "commands": {name: Path("/usr/bin", name).exists()
                     for name in ("say", "osascript", "open", "afplay")},
        "mail_permissions": "Not tested by doctor",
        "audio_audibility": "Requires listener confirmation",
    }


def open_app(app):
    apps = {"Mail", "Messages", "Contacts", "Safari", "Google Chrome", "Finder"}
    if app not in apps:
        raise ValueError(f"Supported apps: {', '.join(sorted(apps))}.")
    run_command(["/usr/bin/open", "-a", app])
    return {"status": "launch_requested", "app": app}

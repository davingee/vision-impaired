"""Files: Spotlight search (the Command-Space index), open, and read text files."""
from pathlib import Path

from common import run_command


def search_files(text, limit=20, name_only=False, folder=None):
    """Search like Command-Space via mdfind; newest first, skipping Library and hidden folders."""
    text = text.strip()
    if not text or text.startswith("-") or not 1 <= limit <= 100:
        raise ValueError("Give search words (not starting with '-') and a limit of 1–100.")
    args = ["/usr/bin/mdfind"]
    if folder:
        args += ["-onlyin", str(Path(folder).expanduser().resolve(strict=True))]
    args += ["-name", text] if name_only else [text]
    found = []
    for line in run_command(args, timeout=30).splitlines():
        path = Path(line)
        if "/Library/" in line or any(part.startswith(".") for part in path.parts):
            continue
        try:
            found.append((path.stat().st_mtime, path))
        except OSError:
            continue
    found.sort(reverse=True)
    return {"count": len(found), "files": [
        {"name": p.name, "folder": str(p.parent), "path": str(p), "is_folder": p.is_dir()}
        for _, p in found[:limit]]}


def open_file(path):
    target = Path(path).expanduser().resolve(strict=True)
    run_command(["/usr/bin/open", str(target)])
    return {"status": "open_requested", "path": str(target)}


def read_text_file(path, max_chars=20000):
    if not 1 <= max_chars <= 100000:
        raise ValueError("max_chars must be between 1 and 100,000.")
    target = Path(path).expanduser().resolve(strict=True)
    if target.suffix.lower() not in {".txt", ".md", ".csv", ".log"}:
        raise ValueError("This first version reads TXT, Markdown, CSV, and log files.")
    with target.open(encoding="utf-8") as handle:
        text = handle.read(max_chars + 1)
    return {"path": str(target), "text": text[:max_chars],
            "truncated": len(text) > max_chars}

"""Command line: run any tool from Terminal (mail, texts, shows, web, files, speech).

Sends texts only when confirmed. No email sending.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from browser import DEFAULT as DEFAULT_BROWSER, browser_tabs, play_show, web_search, click_page, open_url, read_page
from common import doctor, open_app
from files import open_file, read_text_file, search_files
from mail import mail
from speech import DEFAULT_VOICE, Speech, voices
from weather import forecast
from texts import list_chats, read_chat, search_contacts, send_text


def speak(args):
    speech = Speech()
    try:
        text = Path(args.file).read_text() if args.file else sys.stdin.read()
        result = speech.start(text, args.voice, args.rate)
        if speech.process.wait():
            raise RuntimeError("Speech did not finish successfully.")
        result["status"] = "finished"
        return result
    finally:
        speech.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = {}

    def add(name, handler):
        command[name] = handler
        return sub.add_parser(name)

    add("doctor", lambda a: doctor())
    p = add("open-app", lambda a: open_app(a.app))
    p.add_argument("app")

    # Mail
    p = add("mail-list", lambda a: mail("list", limit=a.limit))
    p.add_argument("--limit", type=int, default=5)
    p = add("mail-read", lambda a: mail("read", id=a.id))
    p.add_argument("--id", type=int)
    p = add("mail-draft", lambda a: mail("draft", id=a.id, text=Path(a.file).read_text()))
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--file", required=True, help="UTF-8 reply text file")

    # Texts and contacts
    p = add("contacts", lambda a: search_contacts(a.name))
    p.add_argument("name")
    p = add("texts", lambda a: list_chats(a.limit, a.name))
    p.add_argument("--name")
    p.add_argument("--limit", type=int, default=10)
    p = add("text-read", lambda a: read_chat(a.chat_id, a.limit))
    p.add_argument("chat_id", type=int)
    p.add_argument("--limit", type=int, default=20)
    p = add("text-send", lambda a: send_text(a.chat_id, Path(a.file).read_text(), a.yes))
    p.add_argument("chat_id", type=int)
    p.add_argument("--file", required=True, help="UTF-8 message text file")
    p.add_argument("--yes", action="store_true", help="User confirmed after read-back")

    # Safari and Chrome
    p = add("open-url", lambda a: open_url(a.url, a.browser))
    p.add_argument("url")
    p = add("watch", lambda a: play_show(a.service, a.show, a.profile))
    p.add_argument("service", help="netflix, hulu, or prime")
    p.add_argument("show")
    p.add_argument("--profile", help="default: first of BRAIN_PROFILES")
    p = add("search", lambda a: web_search(a.query, a.browser))
    p.add_argument("query")
    p = add("tabs", lambda a: browser_tabs(a.browser))
    p = add("page", lambda a: read_page(a.browser))
    p = add("click", lambda a: click_page(a.label, a.browser))
    p.add_argument("label")
    for name in ("open-url", "search", "tabs", "page", "click"):
        sub.choices[name].add_argument("--browser", choices=["chrome", "safari"],
                                       default=DEFAULT_BROWSER)

    # Weather
    p = add("weather", lambda a: forecast(a.periods))
    p.add_argument("--periods", type=int, default=4)

    # Files
    p = add("find-files", lambda a: search_files(a.text, a.limit, a.name_only, a.folder))
    p.add_argument("text")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--name-only", action="store_true")
    p.add_argument("--folder")
    p = add("open-file", lambda a: open_file(a.path))
    p.add_argument("path")
    p = add("read-file", lambda a: read_text_file(a.path))
    p.add_argument("path")

    # Speech
    add("voices", lambda a: voices())
    p = add("speak", speak)
    p.add_argument("--voice", default=DEFAULT_VOICE)
    p.add_argument("--rate", default=175, type=int)
    p.add_argument("--file", help="UTF-8 text file; otherwise read stdin")

    args = parser.parse_args()
    try:
        result = command[args.command](args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()

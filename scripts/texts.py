"""Messages and Contacts. Reads Apple's databases read-only; sends via messages.applescript."""
import re
import sqlite3
import tempfile
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import ROOT, run_command

MESSAGES_DB = Path.home() / "Library/Messages/chat.db"
CONTACTS_DIR = Path.home() / "Library/Application Support/AddressBook/Sources"
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def query(db, sql, args=()):
    # Read-only: Bruce never writes Apple's databases.
    try:
        with closing(sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)) as con:
            return con.execute(sql, args).fetchall()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(f"Cannot read {db.name} ({exc}). "
                           "Give the app running Bruce Full Disk Access.") from exc


CONTACTS_SQL = """
SELECT coalesce(nullif(trim(coalesce(r.ZFIRSTNAME, '') || ' ' || coalesce(r.ZLASTNAME, '')), ''),
                r.ZORGANIZATION), 'phones', p.ZFULLNUMBER
FROM ZABCDRECORD r JOIN ZABCDPHONENUMBER p ON p.ZOWNER = r.Z_PK
UNION ALL
SELECT coalesce(nullif(trim(coalesce(r.ZFIRSTNAME, '') || ' ' || coalesce(r.ZLASTNAME, '')), ''),
                r.ZORGANIZATION), 'emails', e.ZADDRESS
FROM ZABCDRECORD r JOIN ZABCDEMAILADDRESS e ON e.ZOWNER = r.Z_PK
"""


def all_contacts():
    people = {}
    for db in sorted(CONTACTS_DIR.glob("*/AddressBook-v22.abcddb")):
        for name, kind, value in query(db, CONTACTS_SQL):
            if name and value:
                person = people.setdefault(name, {"name": name, "phones": [], "emails": []})
                if value not in person[kind]:
                    person[kind].append(value)
    return people


def search_contacts(text, limit=10):
    words = text.lower().split()
    if not words or not 1 <= limit <= 50:
        raise ValueError("Give a name to search and a limit of 1–50.")
    found = [p for name, p in all_contacts().items() if all(w in name.lower() for w in words)]
    return {"contacts": found[:limit], "more": len(found) > limit}


def handle_key(handle):
    """Match '+1 (555) 123-4567' with '5551234567'; emails by lowercase."""
    if "@" in handle:
        return handle.strip().lower()
    return re.sub(r"\D", "", handle)[-10:]


def names_by_handle():
    return {handle_key(value): p["name"] for p in all_contacts().values()
            for value in p["phones"] + p["emails"]}


def apple_time(value):
    return (APPLE_EPOCH + timedelta(microseconds=value // 1000)).astimezone().isoformat(
        timespec="minutes")


def message_text(text, blob):
    if text:
        return text
    if not blob:
        return None
    # ponytail: newer macOS keeps text in an NSArchiver blob. Pull the first NSString
    # ("+", length, UTF-8 bytes) instead of a full typedstream parser; upgrade if Apple changes it.
    start = blob.find(b"NSString")
    if start < 0:
        return None
    i = blob.find(b"+", start) + 1
    if not i:
        return None
    size, i = blob[i], i + 1
    if size == 0x81:
        size, i = int.from_bytes(blob[i:i + 2], "little"), i + 2
    elif size == 0x82:
        size, i = int.from_bytes(blob[i:i + 4], "little"), i + 4
    return blob[i:i + size].decode("utf-8", "replace")


CHATS_SQL = """
SELECT c.ROWID, c.display_name, c.style = 43, j.last,
       (SELECT group_concat(h.id, ',') FROM chat_handle_join ch
        JOIN handle h ON h.ROWID = ch.handle_id WHERE ch.chat_id = c.ROWID)
FROM chat c JOIN (SELECT chat_id, max(message_date) last FROM chat_message_join
                  GROUP BY chat_id) j ON j.chat_id = c.ROWID
ORDER BY j.last DESC
"""


def list_chats(limit=10, name=None):
    if not 1 <= limit <= 50:
        raise ValueError("Limit must be 1–50.")
    names = names_by_handle()
    words = (name or "").lower().split()
    chats = []
    for chat_id, title, group, last, handles in query(MESSAGES_DB, CHATS_SQL):
        people = [names.get(handle_key(h), h) for h in (handles or "").split(",") if h]
        title = title or ", ".join(people) or "Unknown"
        if all(w in title.lower() for w in words):
            chats.append({"chat_id": chat_id, "name": title, "group": bool(group),
                          "last_message": apple_time(last)})
            if len(chats) == limit:
                break
    for chat in chats:
        # is_read stays 0 on texts read on another device; the chat's last-read time is reliable.
        chat["unread"] = query(MESSAGES_DB, """
            SELECT count(*) FROM chat c
            JOIN chat_message_join j ON j.chat_id = c.ROWID
            JOIN message m ON m.ROWID = j.message_id
            WHERE c.ROWID = ? AND m.is_read = 0 AND m.is_from_me = 0
              AND m.associated_message_type = 0
              AND m.date > c.last_read_message_timestamp""", (chat["chat_id"],))[0][0]
    return {"conversations": chats}


def chat_title(chat_id):
    rows = query(MESSAGES_DB, """
        SELECT c.display_name, h.id FROM chat c
        LEFT JOIN chat_handle_join ch ON ch.chat_id = c.ROWID
        LEFT JOIN handle h ON h.ROWID = ch.handle_id WHERE c.ROWID = ?""", (chat_id,))
    if not rows:
        raise ValueError("Unknown conversation ID. List conversations first.")
    names = names_by_handle()
    return rows[0][0] or ", ".join(names.get(handle_key(h), h) for _, h in rows if h) or "Unknown"


def read_chat(chat_id, limit=20):
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be 1–100.")
    names = names_by_handle()
    rows = query(MESSAGES_DB, """
        SELECT m.date, m.is_from_me, h.id, m.text, m.attributedBody, m.cache_has_attachments
        FROM chat_message_join j JOIN message m ON m.ROWID = j.message_id
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        WHERE j.chat_id = ? AND m.associated_message_type = 0
        ORDER BY j.message_date DESC LIMIT ?""", (chat_id, limit))
    if not rows:
        raise ValueError("No messages for that conversation ID. List conversations first.")
    return {"chat_id": chat_id, "messages": [
        {"from": "me" if mine else names.get(handle_key(h or ""), h or "unknown"),
         "time": apple_time(date),
         "text": message_text(text, blob) or ("[attachment]" if attached else "[no text]")}
        for date, mine, h, text, blob, attached in reversed(rows)]}


def send_text(chat_id, text, confirmed=False):
    if not confirmed:
        raise ValueError("Read the recipient and text back; send only after the user says yes.")
    if not text.strip() or len(text) > 5000:
        raise ValueError("Text must contain 1–5,000 characters.")
    found = query(MESSAGES_DB, "SELECT guid FROM chat WHERE ROWID = ?", (chat_id,))
    if not found:
        raise ValueError("Unknown conversation ID. List conversations first.")
    since = int((time.time() - APPLE_EPOCH.timestamp() - 5) * 1e9)
    # A private temporary file keeps the text out of the process command line.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding="utf-8") as body:
        body.write(text)
        body.flush()
        run_command(["/usr/bin/osascript", str(ROOT / "messages.applescript"),
                     found[0][0], body.name], timeout=30)
    # Messages returns nothing useful; the database shows whether it really went out.
    for _ in range(20):
        time.sleep(0.5)
        for error, sent, saved, blob in query(MESSAGES_DB, """
                SELECT m.error, m.is_sent, m.text, m.attributedBody
                FROM chat_message_join j JOIN message m ON m.ROWID = j.message_id
                WHERE j.chat_id = ? AND m.is_from_me = 1 AND m.date >= ?""", (chat_id, since)):
            if message_text(saved, blob) == text:
                if error:
                    return {"status": "failed", "error_code": error}
                if sent:
                    return {"status": "sent", "chat_id": chat_id}
    return {"status": "pending", "chat_id": chat_id,
            "note": "Handed to Messages; not yet confirmed sent."}

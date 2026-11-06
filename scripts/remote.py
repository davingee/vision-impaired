"""Remote help: make sure a helper can reach this Mac over Tailscale with Screen Sharing.

One-time setup (by the helper, see SETUP.md): Tailscale signed in and opening at login,
and System Settings › General › Sharing › Screen Sharing turned on. This module never
changes sharing settings; it only checks them, reconnects Tailscale, and drafts the
message. The text itself goes through send_text_message and its spoken "yes".
"""
import re
import socket
import time

from common import HELPER_NAME, USER_NAME, run_command
from texts import list_chats

# Tailscale gives each connected device an address in 100.64.0.0/10.
TAILSCALE_ADDRESS = re.compile(
    r"inet (100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})\b")


def tailscale_address():
    """This Mac's Tailscale address, or None when Tailscale isn't connected. Read from
    the network interfaces, because the App Store app's CLI often refuses to run."""
    match = TAILSCALE_ADDRESS.search(run_command(["/sbin/ifconfig"]))
    return match.group(1) if match else None


def screen_sharing_on():
    """Screen Sharing listens on port 5900 when it is turned on."""
    try:
        with socket.create_connection(("127.0.0.1", 5900), timeout=1):
            return True
    except OSError:
        return False


def prepare_remote_help(wait_seconds=20):
    address = tailscale_address()
    if not address:
        run_command(["/usr/bin/open", "-g", "-a", "Tailscale"])  # Reconnects if signed in.
        deadline = time.time() + wait_seconds
        while not address and time.time() < deadline:
            time.sleep(1)
            address = tailscale_address()
    sharing = screen_sharing_on()
    problems = []
    if not address:
        problems.append("Tailscale is not connected (it may need signing in again)")
    if not sharing:
        problems.append("Screen Sharing is turned off in System Settings")
    helper = HELPER_NAME or "the helper"
    chats = list_chats(limit=5, name=HELPER_NAME)["conversations"] if HELPER_NAME else []
    who = USER_NAME or "Someone"
    link = f"vnc://{address}" if address else None
    message = (f"{who} asked for help with the Mac. Connect with Screen Sharing: {link}"
               if link else f"{who} asked for help with the Mac, but it isn't reachable "
                            f"remotely right now: {'; '.join(problems)}.")
    return {
        "ready": not problems,
        "connect_link": link,
        "problems": problems,
        "helper": helper,
        "helper_chat_id": chats[0]["chat_id"] if chats else None,
        "message_to_send": message,
        "note": (f"Read the message to the user and, if they say yes, send it to {helper} "
                 "with send_text_message using helper_chat_id. Tell the user help has "
                 "been asked for, and that the helper may see their screen."
                 if chats else f"No text conversation with {helper} found; tell the user."),
    }

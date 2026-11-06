"""Apple Mail through mail.js. Replies are sent only after the user confirms."""
from datetime import datetime
from email.utils import parseaddr

from common import jxa


def friendly(message):
    """Sender name and local time, ready to say aloud; the address stays available."""
    name, address = parseaddr(message.get("sender", ""))
    message["sender"], message["sender_email"] = name or address, address
    if message.get("received"):
        # mail.js reports UTC; the user needs their own clock time.
        when = datetime.fromisoformat(message["received"].replace("Z", "+00:00")).astimezone()
        day = "today" if when.date() == datetime.now().date() else when.strftime("%A %B %-d")
        message["received"] = f"{day} at {when.strftime('%-I:%M %p')}"
    return message


def send_reply(message_id, text, confirmed=False):
    """Reply to an inbox message. Replies only: the recipient comes from that message,
    never from the model."""
    if not confirmed:
        raise ValueError("Read the recipient, subject, and exact text back; send only "
                         "after the user says yes.")
    return mail("send", id=message_id, text=text, confirmed=True)


def mail(action, **params):
    result = jxa("mail.js", {"action": action, **params})
    if action == "list":
        result["messages"] = [friendly(m) for m in result["messages"]]
    elif action == "read":
        friendly(result)
    return result

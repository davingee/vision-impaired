"""Apple Mail through mail.js. No email sending."""
from datetime import datetime
from email.utils import parseaddr

from common import jxa


def friendly(message):
    """Sender name and local time, ready to say aloud; the address stays available."""
    name, address = parseaddr(message.get("sender", ""))
    message["sender"], message["sender_email"] = name or address, address
    if message.get("received"):
        # mail.js reports UTC; Bruce needs his own clock time.
        when = datetime.fromisoformat(message["received"].replace("Z", "+00:00")).astimezone()
        day = "today" if when.date() == datetime.now().date() else when.strftime("%A %B %-d")
        message["received"] = f"{day} at {when.strftime('%-I:%M %p')}"
    return message


def mail(action, **params):
    result = jxa("mail.js", {"action": action, **params})
    if action == "list":
        result["messages"] = [friendly(m) for m in result["messages"]]
    elif action == "read":
        friendly(result)
    return result

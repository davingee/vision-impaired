"""Safari and Chrome: open pages, list tabs, read and click the front page."""
import os
import re
import time
from difflib import SequenceMatcher
from urllib.parse import quote_plus, urlparse

from common import checkpoint, jxa, run_command

# Other people's Netflix profiles. Bruce watches only as Scott or Bruce.
OTHER_PROFILES = {"kids", "drew", "kyrie"}
BROWSERS = {"chrome": "Google Chrome", "safari": "Safari"}
# Safari by default: Chrome on this Mac is managed and locks page control.
DEFAULT = os.environ.get("BRAIN_BROWSER", "safari")
JS_SETTING = {
    "chrome": "In Chrome: View › Developer › Allow JavaScript from Apple Events.",
    "safari": "In Safari: Settings › Advanced › Show features for web developers, "
              "then Develop › Allow JavaScript from Apple Events.",
}


def app_name(browser):
    if browser not in BROWSERS:
        raise ValueError("Browser must be 'chrome' or 'safari'.")
    return BROWSERS[browser]


def open_url(url, browser=DEFAULT, same_tab=False):
    if urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("Only http and https addresses can be opened.")
    if same_tab:
        jxa("browser.js", {"app": app_name(browser), "action": "navigate", "url": url})
    else:
        run_command(["/usr/bin/open", "-a", app_name(browser), url])
    result = {"status": "open_requested", "browser": browser, "url": url}
    time.sleep(3)  # Let it load, then return the content so the assistant can answer.
    try:
        result["page"] = read_page(browser, 4000)
    except RuntimeError as exc:
        result["page_error"] = str(exc)
    return result


def web_search(query, browser=DEFAULT):
    if not query.strip() or len(query) > 300:
        raise ValueError("Give search words (up to 300 characters).")
    return open_url("https://www.google.com/search?q=" + quote_plus(query.strip()), browser)


def browser_tabs(browser=DEFAULT):
    return jxa("browser.js", {"app": app_name(browser), "action": "tabs"})


def page(browser=DEFAULT, action="read", **params):
    try:
        return jxa("browser.js", {"app": app_name(browser), "action": action, **params})
    except RuntimeError as exc:
        if "JavaScript" in str(exc):
            raise RuntimeError("Page control is off in this browser. It needs a one-time "
                               f"setup by Scott, not Bruce: {JS_SETTING[browser]}") from exc
        raise


def read_page(browser=DEFAULT, max_chars=8000):
    if not 100 <= max_chars <= 50000:
        raise ValueError("max_chars must be 100–50,000.")
    return page(browser, "read", max_chars=max_chars)


def click_page(label, browser=DEFAULT):
    if not label.strip() or len(label) > 200:
        raise ValueError("Give the visible label of a link or button.")
    if label.strip().lower() in OTHER_PROFILES:
        raise ValueError("Use only the Scott or Bruce profile.")
    result = page(browser, "click", label=label.strip())
    if result.get("status") == "clicked":
        time.sleep(2.5)  # Let the next page load so the model can confirm, not guess.
        after = read_page(browser, 600)
        result["now_showing"] = {"title": after["title"], "url": after["url"],
                                 "text": after["text"]}
    return result


def wait_for(found, browser, seconds=12):
    """Re-read the page until found(controls) returns something; pages load late."""
    deadline = time.time() + seconds
    while True:
        checkpoint()
        result = found(read_page(browser, 500)["controls"])
        if result or time.time() > deadline:
            return result
        time.sleep(1)


# Per-service pages and play buttons. Buttons are label prefixes, tried in order.
SERVICES = {
    "netflix": {"profiles": "https://www.netflix.com/ProfilesGate",
                "search": "https://www.netflix.com/search?q=",
                "buttons": ("Resume", "Play")},
    # Hulu ignores ?q=, so its search box gets typed into instead.
    # Hulu and Prime have no Bruce/Scott profile picker here; skipping it saves ~10 s.
    "hulu": {"profiles": None,
             "search": "https://www.hulu.com/search", "type_search": True,
             "buttons": ("Resume", "Watch Next Episode", "Keep Watching", "Continue",
                         "Play", "Start Watching", "Watch Now")},
    "prime video": {"profiles": None,
                    "search": "https://www.amazon.com/gp/video/search?phrase=",
                    "buttons": ("Resume", "Continue watching", "Play", "Watch now")},
}
SERVICE_NAMES = {"netflix": "netflix", "hulu": "hulu", "prime": "prime video",
                 "prime video": "prime video", "amazon": "prime video",
                 "amazon prime": "prime video", "amazon prime video": "prime video"}
# Never press these while trying to play: they cost money or change the account.
NEVER_PRESS = re.compile(r"buy|rent|trial|subscribe|sign ?up|upgrade|add-on|\$", re.IGNORECASE)


def play_button(controls, buttons):
    for prefix in buttons:
        for label in controls:
            if label.lower().startswith(prefix.lower()) and not NEVER_PRESS.search(label):
                return label
    return None


def matching_titles(show, controls):
    """Titles containing every spoken word; failing that, near spellings, since speech
    recognition hears "Elsbeth" as "Elspeth"."""
    # Skip "Search for X" (Hulu) and "Search instead for X" (Amazon's spelling fix).
    usable = [c for c in controls
              if not NEVER_PRESS.search(c) and not re.match(r"search (for|instead)", c, re.I)]
    words = show.lower().replace(":", "").split()
    exact = [c for c in usable if all(w in c.lower().replace(":", "") for w in words)]
    if exact:
        return exact
    near = lambda c: SequenceMatcher(None, show.lower(), c.lower()[:len(show) + 4]).ratio()
    return [c for c in usable if len(c) >= 3 and near(c) >= 0.75]


def play_show(service, show, profile="Bruce", browser=DEFAULT):
    """Whole streaming flow in code, so a small model only has to name the show:
    pick the profile, search, open the best-matching title, press Resume or Play."""
    site = SERVICES.get(SERVICE_NAMES.get(service.strip().lower(), ""))
    if not site:
        raise ValueError("Service must be Netflix, Hulu, or Prime Video.")
    show = show.strip()
    if not show:
        raise ValueError("Say which show to play.")
    if profile.strip().lower() not in {"bruce", "scott"}:
        raise ValueError("Use only the Scott or Bruce profile.")
    profile = profile.strip().title()
    if site["profiles"]:
        open_url(site["profiles"], browser)
        if wait_for(lambda controls: profile in controls, browser, seconds=6):
            click_page(profile, browser)
    first = not site["profiles"]  # The first page opens a new tab; the rest reuse it.
    if site.get("type_search"):
        open_url(site["search"], browser, same_tab=not first)
        page(browser, "type", text=show)
        # The page already shows popular tiles (maybe this very show); wait for the
        # typed results to replace them, or the wrong tile gets clicked.
        wait_for(lambda controls: any(c.lower().startswith("search for") for c in controls),
                 browser)
    else:
        open_url(site["search"] + quote_plus(show), browser, same_tab=not first)
    candidates = wait_for(lambda controls: matching_titles(show, controls), browser)
    if not candidates:
        return {"status": "not_found", "show": show,
                "note": "The search showed no title with those words. Is Bruce signed in?"}
    # "Blacklist" should pick "The Blacklist", not "The Wake: Blacklist".
    # Hulu labels read "High Potential High Potential SERIES": a title that starts with
    # the show's name wins first, then the closest overall match.
    title = max(candidates, key=lambda c: (c.lower().startswith(show.lower()),
                                           SequenceMatcher(None, show.lower(), c.lower()).ratio()))
    checkpoint()
    details = click_page(title, browser)
    button = wait_for(lambda controls: play_button(controls, site["buttons"]), browser)
    if not button:
        seen = [c for c in read_page(browser, 100)["controls"] if not NEVER_PRESS.search(c)]
        return {"status": "no_play_button", "show": title, "buttons_seen": seen[:25],
                "note": "Opened the show but found no button I know. If one of buttons_seen "
                        "plays it, press it with click_web_page."}
    active = read_page(browser, 100).get("active_profile")  # Netflix only; read before playing.
    if active and active != profile:
        return {"status": "wrong_profile", "active_profile": active, "wanted": profile,
                "note": "The service is on a different profile; nothing was played."}
    checkpoint()
    before = read_page(browser, 100)["url"]
    after = click_page(button, browser).get("now_showing", {})
    playing = wait_for_video(browser)
    opened = playing or after.get("url", "") != before or "/watch" in after.get("url", "")
    return {"status": "playing" if playing else "video_opened" if opened else "not_confirmed",
            "show": title, "profile": active or profile, "pressed": button,
            "note": "A video is playing; ask Bruce if he hears it." if playing else
                    "The video page opened but isn't playing yet." if opened else
                    "Pressed the button but nothing changed."}


def wait_for_video(browser, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        checkpoint()
        if read_page(browser, 100).get("video_playing"):
            return True
        time.sleep(1)
    return False

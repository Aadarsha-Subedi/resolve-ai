import re

from accounts.constants.settings import UNKNOWN_DEVICE_LABEL

# Order matters: Edge and Opera also say "Chrome"; Chrome also says "Safari".
_BROWSERS = [
    ("Edge", re.compile(r"Edg(?:e|A|iOS)?/")),
    ("Opera", re.compile(r"OPR/|Opera")),
    ("Firefox", re.compile(r"Firefox/|FxiOS/")),
    ("Chrome", re.compile(r"Chrome/|CriOS/")),
    ("Safari", re.compile(r"Safari/")),
]
_SYSTEMS = [
    ("Android", re.compile(r"Android")),
    ("iOS", re.compile(r"iPhone|iPad|iPod")),
    ("Windows", re.compile(r"Windows")),
    ("macOS", re.compile(r"Mac OS X|Macintosh")),
    ("ChromeOS", re.compile(r"CrOS")),
    ("Linux", re.compile(r"Linux|X11")),
]


def device_label(user_agent: str) -> str:
    """'Browser on OS' parsed from a User-Agent string."""
    browser = next((n for n, rx in _BROWSERS if rx.search(user_agent)), None)
    system = next((n for n, rx in _SYSTEMS if rx.search(user_agent)), None)
    if browser and system:
        return f"{browser} on {system}"
    return browser or system or UNKNOWN_DEVICE_LABEL

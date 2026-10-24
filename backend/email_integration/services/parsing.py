"""Turning Gmail payloads and email text into what tickets store."""

import base64
import re
from email.utils import getaddresses
from html.parser import HTMLParser

from email_integration.constants.settings import QUOTED_BODY_MAX_LENGTH

_MESSAGE_ID = re.compile(r"<[^<>\s]+>")
# "On Tue, 20 Oct 2026 at 10:00, Jane <jane@x.com> wrote:" and common localisations.
_QUOTE_INTRO = re.compile(
    r"^(on .{5,200}wrote:|-{2,}\s*original message\s*-{2,}|from:\s.+)$", re.IGNORECASE
)


def message_ids(*header_values: str) -> list[str]:
    """Every <message-id> mentioned in headers such as In-Reply-To and References."""
    found: list[str] = []
    for value in header_values:
        found.extend(_MESSAGE_ID.findall(value or ""))
    return list(dict.fromkeys(found))


def parse_sender(from_header: str) -> tuple[str, str]:
    """(name, address) of the first address in a From header; address is lower-cased."""
    addresses = getaddresses([from_header or ""])
    if not addresses:
        return "", ""
    name, address = addresses[0]
    return name.strip(), address.strip().lower()


def clean_header(value: str) -> str:
    """No CR or LF: a header value must never be able to start another header."""
    return re.sub(r"[\r\n]+", " ", value).strip()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in ("br", "p", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()


def _decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def extract_text(payload: dict) -> str:
    """Plain text of a Gmail message payload; HTML is reduced to text, never kept as HTML."""
    plain: list[str] = []
    html: list[str] = []

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        if part.get("parts"):
            for child in part["parts"]:
                walk(child)
        elif body.get("data"):
            if mime == "text/plain":
                plain.append(_decode(body["data"]))
            elif mime == "text/html":
                html.append(_decode(body["data"]))

    walk(payload)
    if plain:
        return "\n".join(plain).strip()
    return html_to_text("\n".join(html)) if html else ""


def strip_quoted_reply(text: str) -> str:
    """Keep what the customer wrote, drop the quoted earlier conversation and the signature
    marker, and cap the length."""
    kept: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if _QUOTE_INTRO.match(stripped) or stripped == "--":
            break  # everything after is quoted history or a signature
        kept.append(line)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return cleaned[:QUOTED_BODY_MAX_LENGTH]

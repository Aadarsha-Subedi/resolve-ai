"""Verified claims: keeps a claim from the model only when its quote is really in the passage.

The model returns claims, each with the exact words it relied on and the number of the passage
they came from. A quote that is found in that passage (ignoring case, spacing, Markdown
marks and typographic quotes) proves the words exist there; it does not prove the claim
follows from them. A claim with no found quote is dropped."""

import json
import logging
import re
import unicodedata
from collections import Counter

from knowledge.constants import settings as cfg

logger = logging.getLogger(__name__)

_MARK = re.compile(r"\[\d{1,2}\]")
_STRIPPED = set("*_`#>~|\\")
_PUNCTUATION = str.maketrans(
    {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}
)


def _normalize(text: str) -> tuple[str, list[int]]:
    """The comparable form of `text` and, for each of its characters, the index of the
    original character it came from."""
    out: list[str] = []
    origin: list[int] = []
    pending_space = False
    for index, char in enumerate(text):
        for piece in unicodedata.normalize("NFKC", char).casefold():
            piece = piece.translate(_PUNCTUATION)
            if piece in _STRIPPED:
                continue
            if piece.isspace():
                pending_space = bool(out)
                continue
            if pending_space:
                out.append(" ")
                origin.append(index)
                pending_space = False
            out.append(piece)
            origin.append(index)
    return "".join(out), origin


def _find_quote(quote: str, passage: str) -> tuple[int, int] | None:
    """(start, end) of `quote` in the original `passage` text, or None."""
    needle, _ = _normalize(quote)
    if not needle:
        return None
    haystack, origin = _normalize(passage)
    position = haystack.find(needle)
    if position < 0:
        return None
    return origin[position], origin[position + len(needle) - 1] + 1


def _cite(item, passages: list[str]) -> tuple[dict | None, str]:
    """(cite, "") when the quote is found in its passage, else (None, why it was dropped)."""
    if not isinstance(item, dict):
        return None, "bad_cite"
    number, quote = item.get("n"), item.get("quote")
    if isinstance(number, bool) or not isinstance(number, int):
        return None, "bad_cite"
    if not isinstance(quote, str) or not 1 <= number <= len(passages):
        return None, "bad_passage_number"
    words = len(quote.split())
    if not cfg.CLAIM_QUOTE_MIN_WORDS <= words <= cfg.CLAIM_QUOTE_MAX_WORDS:
        return None, "quote_length"
    passage = passages[number - 1]
    found = _find_quote(quote, passage)
    if found is None:
        return None, "quote_not_found"
    start, end = found
    room = cfg.CLAIM_CONTEXT_CHARS
    return {
        "n": number,
        # The passage's own words, so the page can show and mark them in place.
        "before": passage[max(0, start - room) : start],
        "quote": passage[start:end],
        "after": passage[end : end + room],
    }, ""


def verify_claims(raw: str, passages: list[str]) -> list[dict]:
    """The verified claims in the model's JSON, as {"text", "cites": [{"n", "before", "quote",
    "after"}]}; [] when the output is unusable or nothing could be verified. `passages` are the
    full texts of the excerpts, numbered from 1."""
    try:
        data = json.loads(raw)
    except TypeError, ValueError:
        logger.info("Claims: the model's output was not JSON")
        return []
    items = data.get("claims") if isinstance(data, dict) else None
    if not isinstance(items, list):
        logger.info("Claims: the model's output had no claims list")
        return []
    claims = []
    dropped: Counter = Counter()
    for item in items[: cfg.CLAIM_MAX_CLAIMS]:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            continue
        text = " ".join(_MARK.sub("", item["text"]).split())[: cfg.CLAIM_TEXT_MAX_CHARS]
        raw_cites = item.get("cites")
        if not text or not isinstance(raw_cites, list):
            dropped["bad_claim"] += 1
            continue
        cites, seen = [], set()
        for raw_cite in raw_cites[: cfg.CLAIM_MAX_CITES]:
            cite, reason = _cite(raw_cite, passages)
            if cite is None:
                dropped[reason] += 1
            elif (cite["n"], cite["quote"]) not in seen:
                seen.add((cite["n"], cite["quote"]))
                cites.append(cite)
        if cites:
            claims.append({"text": text, "cites": cites})
        else:
            dropped["claim_without_verified_quote"] += 1
    # Counts only: the text of the question, answer and passages is never logged.
    logger.info(
        "Claims: %d proposed, %d kept, dropped %s",
        len(items),
        len(claims),
        dict(dropped),
    )
    return claims


def answer_text(claims: list[dict]) -> str:
    """The claims as one plain answer with [n] markers, the shape older clients read. Whole
    claims only: it stops before the first claim that would pass the length limit."""
    answer = ""
    for claim in claims:
        numbers = sorted({c["n"] for c in claim["cites"]})
        part = claim["text"] + " " + "".join(f"[{n}]" for n in numbers)
        if len(answer) + len(part) + 1 > cfg.ANSWER_MAX_CHARS:
            break
        answer = f"{answer} {part}" if answer else part
    return answer

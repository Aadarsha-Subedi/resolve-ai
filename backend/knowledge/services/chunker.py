"""Split Markdown (an article, or the text of an uploaded document) into passages for
search and citations.

Pure function, no database. Rules:
- "#" to "###" headings (outside code fences) start a new section; every passage carries
  its heading path, which begins with the article title.
- A section is cut at blank lines into paragraphs, then packed into passages of about
  CHUNK_MIN_CHARS to CHUNK_MAX_CHARS. Text longer than the maximum is cut at sentence,
  then word boundaries.
- A fenced code block is never split unless it is larger than CHUNK_CODE_MAX_CHARS,
  and then only between lines.
- A table (lines starting with "|") is cut between rows, and every piece repeats the
  header row so it stays readable on its own.
- Sections without body text produce no passage; a tiny last passage is merged into
  the one before it.
- Documents: `chunk_document` takes the pages of a PDF (or one unnumbered page). Headings
  carry over from page to page, a passage never crosses a page and records its page number,
  and a long paragraph that has to be cut overlaps its neighbour by one sentence.
"""

import re
from dataclasses import dataclass

from knowledge.constants.settings import (
    CHUNK_CODE_MAX_CHARS,
    CHUNK_HEADING_PATH_MAX_LENGTH,
    CHUNK_HEADING_SEPARATOR,
    CHUNK_MAX_CHARS,
    CHUNK_MAX_HEADING_LEVEL,
    CHUNK_MIN_CHARS,
    CHUNK_OVERLAP_CHARS,
)

_HEADING = re.compile(rf"^(#{{1,{CHUNK_MAX_HEADING_LEVEL}}})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


@dataclass(frozen=True)
class ChunkDraft:
    heading_path: str
    text: str
    page: int | None = None


def chunk_markdown(title: str, content: str) -> list[ChunkDraft]:
    return _chunk(title, content, [], page=None, overlap=0)


def chunk_document(title: str, pages: list[tuple[int | None, str]]) -> list[ChunkDraft]:
    """Passages of an uploaded document, given as (page number or None, Markdown) pairs."""
    stack: list[tuple[int, str]] = []  # headings stay in force on the following pages
    chunks: list[ChunkDraft] = []
    for page, content in pages:
        chunks.extend(
            _chunk(title, content, stack, page=page, overlap=CHUNK_OVERLAP_CHARS)
        )
    return chunks


def _chunk(
    title: str,
    content: str,
    stack: list[tuple[int, str]],
    page: int | None,
    overlap: int,
) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    for path, body_lines in _sections(title, content, stack):
        paragraphs = _paragraphs(body_lines)
        for text in _pack(paragraphs, overlap):
            chunks.append(ChunkDraft(path, text, page))
    return chunks


def _heading_path(title: str, stack: list[tuple[int, str]]) -> str:
    names = [name for _, name in stack]
    if names and names[0].casefold() == title.strip().casefold():
        names = names[1:]  # a "# Title" heading that repeats the article title
    parts = [title.strip(), *names]
    return CHUNK_HEADING_SEPARATOR.join(parts)[:CHUNK_HEADING_PATH_MAX_LENGTH]


def _sections(title: str, content: str, stack: list[tuple[int, str]]):
    """Yield (heading_path, body_lines) for the text before and after each heading.
    `stack` is the heading path in force; it is updated in place."""
    body: list[str] = []
    fence = None
    for line in content.splitlines():
        fence_match = _FENCE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
        heading = None if fence or fence_match else _HEADING.match(line)
        if heading:
            yield _heading_path(title, stack), body
            level, name = len(heading.group(1)), heading.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, name))
            body = []
        else:
            body.append(line)
    yield _heading_path(title, stack), body


def _paragraphs(lines: list[str]) -> list[str]:
    """Blank-line separated blocks; a fenced code block is one block."""
    blocks: list[str] = []
    current: list[str] = []
    fence = None

    def flush():
        text = "\n".join(current).strip()
        if text:
            blocks.append(text)
        current.clear()

    for line in lines:
        fence_match = _FENCE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                if current:
                    flush()
                fence = marker
            elif fence == marker:
                current.append(line)
                fence = None
                flush()
                continue
        if fence is None and not line.strip():
            flush()
        else:
            current.append(line)
    flush()
    return blocks


def _split_long(block: str, overlap: int = 0) -> list[str]:
    """Cut a block longer than the maximum into pieces no longer than the maximum.
    With `overlap`, a piece starts with the previous piece's last sentence if that is
    short enough."""
    if block.lstrip().startswith(("```", "~~~")):
        if len(block) <= CHUNK_CODE_MAX_CHARS:
            return [block]
        return _split_lines(block, CHUNK_CODE_MAX_CHARS)
    if len(block) <= CHUNK_MAX_CHARS:
        return [block]
    if (
        _is_table(block)
        and len("\n".join(block.splitlines()[:2])) <= CHUNK_MAX_CHARS // 2
    ):
        return _split_table(block)
    pieces: list[str] = []
    current = ""
    last_part = ""
    for sentence in _SENTENCE_END.split(block):
        for part in _split_words(sentence):
            if current and len(current) + 1 + len(part) > CHUNK_MAX_CHARS:
                pieces.append(current)
                keep = last_part if 0 < len(last_part) <= overlap else ""
                if keep and len(keep) + 1 + len(part) <= CHUNK_MAX_CHARS:
                    current = f"{keep} {part}"
                else:
                    current = part
            else:
                current = f"{current} {part}".strip()
            last_part = part
    if current:
        pieces.append(current)
    return pieces


def _is_table(block: str) -> bool:
    lines = block.splitlines()
    return (
        len(lines) >= 3
        and all(line.lstrip().startswith("|") for line in lines)
        and bool(_TABLE_SEPARATOR.match(lines[1]))
    )


def _split_table(block: str) -> list[str]:
    """Cut a Markdown table between rows; each piece repeats the header and separator."""
    lines = block.splitlines()
    header = "\n".join(lines[:2])
    pieces: list[str] = []
    current = header
    for row in lines[2:]:
        if len(row) > CHUNK_MAX_CHARS - len(header) - 1:
            # A single row longer than a passage is cut: rare, and its first cells matter most.
            row = row[: CHUNK_MAX_CHARS - len(header) - 1]
        if current != header and len(current) + 1 + len(row) > CHUNK_MAX_CHARS:
            pieces.append(current)
            current = header
        current = f"{current}\n{row}"
    if current != header:
        pieces.append(current)
    return pieces


def _split_lines(block: str, limit: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for line in block.splitlines():
        if current and len(current) + 1 + len(line) > limit:
            pieces.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        pieces.append(current)
    return pieces


def _split_words(text: str) -> list[str]:
    """Cut text that is itself longer than the maximum at word boundaries."""
    if len(text) <= CHUNK_MAX_CHARS:
        return [text]
    pieces: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > CHUNK_MAX_CHARS:  # an unbroken string such as a long URL
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:CHUNK_MAX_CHARS])
            word = word[CHUNK_MAX_CHARS:]
        if current and len(current) + 1 + len(word) > CHUNK_MAX_CHARS:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces


def _pack(paragraphs: list[str], overlap: int = 0) -> list[str]:
    """Greedily join paragraphs up to the maximum; merge a tiny last piece backwards."""
    packed: list[str] = []
    current = ""
    for paragraph in paragraphs:
        for piece in _split_long(paragraph, overlap):
            if (
                current
                and len(current) + 2 + len(piece) > CHUNK_MAX_CHARS
                or current
                and len(current) >= CHUNK_MIN_CHARS
            ):
                packed.append(current)
                current = piece
            else:
                current = f"{current}\n\n{piece}" if current else piece
    if current:
        if (
            packed
            and len(current) < CHUNK_MIN_CHARS
            and len(packed[-1]) + 2 + len(current) <= CHUNK_MAX_CHARS
        ):
            packed[-1] = f"{packed[-1]}\n\n{current}"
        else:
            packed.append(current)
    return packed

"""Markdown helpers shared by the PDF and DOCX parsers."""


def _cell(value: object) -> str:
    text = "" if value is None else " ".join(str(value).split())
    return text.replace("|", "\\|")


def table_to_markdown(rows: list[list[object]]) -> str:
    """A Markdown table whose first row is the header. Empty rows are dropped; returns ""
    when nothing is left, so callers can skip it."""
    cleaned = [[_cell(value) for value in row] for row in rows]
    cleaned = [row for row in cleaned if any(row)]
    if not cleaned:
        return ""
    width = max(len(row) for row in cleaned)
    cleaned = [row + [""] * (width - len(row)) for row in cleaned]
    lines = ["| " + " | ".join(cleaned[0]) + " |", "|" + " --- |" * width]
    lines.extend("| " + " | ".join(row) + " |" for row in cleaned[1:])
    return "\n".join(lines)

from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from email_integration.constants import settings as cfg
from email_integration.services.parsing import clean_header


def build_reply(
    *,
    from_name: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    in_reply_to: str = "",
    references: list[str] | None = None,
) -> bytes:
    """A plain-text reply. Header values are stripped of line breaks (no header injection)
    and the body is plain text only."""
    message = EmailMessage()
    message["From"] = formataddr((clean_header(from_name), clean_header(from_email)))
    message["To"] = clean_header(to_email)
    message["Subject"] = clean_header(subject)[: cfg.SUBJECT_MAX_LENGTH]
    message["Message-ID"] = make_msgid(domain=from_email.rpartition("@")[2] or None)
    if in_reply_to:
        message["In-Reply-To"] = clean_header(in_reply_to)
    if references:
        message["References"] = " ".join(clean_header(r) for r in references)
    message.set_content(body)
    return message.as_bytes()


def reply_subject(ticket_subject: str, number: int) -> str:
    base = clean_header(ticket_subject)
    if not base.lower().startswith("re:"):
        base = cfg.SUBJECT_PREFIX + base
    return f"{base} [#{number}]"

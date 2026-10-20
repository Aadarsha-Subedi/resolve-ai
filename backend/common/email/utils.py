def normalize_email(email: str) -> str:
    """Canonical form used for lookups and storage: trimmed and lower-cased."""
    return email.strip().lower()


def mask_email(email: str) -> str:
    """j***@example.com: enough for the owner to recognise it, not to reuse it."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


_GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def canonical_email_key(email: str) -> str:
    """Key for 'is this the same mailbox?' comparisons (invitations).

    Gmail ignores dots and everything after '+' in the local part, and
    googlemail.com is an alias of gmail.com, so x.y+z@googlemail.com and
    xy@gmail.com are one mailbox. Other domains (including Google Workspace) are
    only lower-cased, because dots and '+' are not guaranteed to be ignored there.
    Never use the key for sending or display; keep the address as typed.
    """
    email = normalize_email(email)
    local, _, domain = email.rpartition("@")
    if domain in _GMAIL_DOMAINS:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"

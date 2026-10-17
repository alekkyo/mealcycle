import re

APP = "/_allauth/app/v1"
CODE_RE = re.compile(r"\b(\d{3}-\d{3})\b")


def extract_code(message) -> str:
    """Return the 6-digit code (as 'ddd-ddd') from an email's subject."""
    match = CODE_RE.search(message.subject)
    assert match, f"no code in subject: {message.subject!r}"
    return match.group(1)

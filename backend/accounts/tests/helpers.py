import re

from django.core import mail

APP = "/_allauth/app/v1"
CODE_RE = re.compile(r"\b(\d{3}-\d{3})\b")


def extract_code(message) -> str:
    """Return the 6-digit code (as 'ddd-ddd') from an email's subject."""
    match = CODE_RE.search(message.subject)
    assert match, f"no code in subject: {message.subject!r}"
    return match.group(1)


def _confirm(client, path, payload, session_token):
    return client.post(path, payload, format="json", HTTP_X_SESSION_TOKEN=session_token)


def signup(client, email: str) -> dict:
    """Sign up with email + emailed code; return the authenticated response JSON."""
    mail.outbox.clear()
    response = client.post(f"{APP}/auth/signup", {"email": email}, format="json")
    session_token = response.json()["meta"]["session_token"]
    code = extract_code(mail.outbox[-1])
    response = _confirm(
        client, f"{APP}/auth/email/verify", {"key": code}, session_token
    )
    assert response.status_code == 200, response.json()
    return response.json()


def login(client, email: str) -> dict:
    """Log in with an emailed code; return the authenticated response JSON."""
    mail.outbox.clear()
    response = client.post(f"{APP}/auth/code/request", {"email": email}, format="json")
    session_token = response.json()["meta"]["session_token"]
    code = extract_code(mail.outbox[-1])
    response = _confirm(
        client, f"{APP}/auth/code/confirm", {"code": code}, session_token
    )
    assert response.status_code == 200, response.json()
    return response.json()

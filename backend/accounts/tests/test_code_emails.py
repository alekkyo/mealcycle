import re

import pytest
from django.core import mail

from accounts.models import User
from accounts.tests.helpers import APP, extract_code

pytestmark = pytest.mark.django_db

SUBJECT_RE = re.compile(r"^Your MealCycle code: \d{3}-\d{3}$")


def _verified_user(email="alex@example.com"):
    # create_user also records a verified primary EmailAddress (see add_primary_email)
    return User.objects.create_user(email=email)


def test_signup_email_subject_and_body(api_client):
    api_client.post(f"{APP}/auth/signup", {"email": "new@example.com"}, format="json")
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert SUBJECT_RE.match(message.subject), message.subject
    code = extract_code(message)
    assert code in message.body
    assert "10 minutes" in message.body


def test_login_code_email_subject_and_body(api_client):
    _verified_user()
    api_client.post(
        f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json"
    )
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert SUBJECT_RE.match(message.subject), message.subject
    assert extract_code(message) in message.body


def test_login_code_accepted_without_dash(api_client):
    _verified_user()
    response = api_client.post(
        f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json"
    )
    session_token = response.json()["meta"]["session_token"]
    code = extract_code(mail.outbox[0]).replace("-", "")
    response = api_client.post(
        f"{APP}/auth/code/confirm",
        {"code": code},
        format="json",
        HTTP_X_SESSION_TOKEN=session_token,
    )
    assert response.status_code == 200, response.json()

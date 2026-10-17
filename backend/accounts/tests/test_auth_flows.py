from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from accounts.models import Profile, User
from accounts.tests.helpers import APP, extract_code, login, signup

pytestmark = pytest.mark.django_db


def _request_code(client, email):
    mail.outbox.clear()
    response = client.post(f"{APP}/auth/code/request", {"email": email}, format="json")
    return response.json()["meta"]["session_token"], extract_code(mail.outbox[-1])


def _confirm_code(client, code, session_token):
    return client.post(
        f"{APP}/auth/code/confirm",
        {"code": code},
        format="json",
        HTTP_X_SESSION_TOKEN=session_token,
    )


def test_signup_returns_tokens_and_creates_one_user_and_profile(api_client):
    body = signup(api_client, "new@example.com")
    assert body["meta"]["access_token"]
    assert body["meta"]["refresh_token"]
    assert User.objects.filter(email="new@example.com").count() == 1
    assert Profile.objects.filter(user__email="new@example.com").count() == 1


def test_returning_user_does_not_duplicate_profile(api_client):
    signup(api_client, "alex@example.com")
    body = login(api_client, "alex@example.com")
    assert body["meta"]["access_token"]
    assert User.objects.count() == 1
    assert Profile.objects.count() == 1


def test_login_with_different_case_email_hits_same_account(api_client):
    signup(api_client, "alex@example.com")
    login(api_client, "Alex@Example.COM")
    assert User.objects.count() == 1


def test_wrong_code_three_times_burns_the_code(api_client):
    signup(api_client, "alex@example.com")
    session_token, real_code = _request_code(api_client, "alex@example.com")
    statuses = [
        _confirm_code(api_client, "000-000", session_token).status_code
        for _ in range(3)
    ]
    assert statuses == [400, 400, 400]
    response = _confirm_code(api_client, real_code, session_token)
    assert response.status_code == 409  # code burned: the pending login is gone


def test_expired_code_is_rejected(api_client):
    signup(api_client, "alex@example.com")
    session_token, code = _request_code(api_client, "alex@example.com")
    later = timezone.now() + timedelta(minutes=11)
    with (
        patch("django.utils.timezone.now", return_value=later),
        patch("time.time", return_value=later.timestamp()),
    ):
        response = _confirm_code(api_client, code, session_token)
    assert response.status_code == 409  # expired: the pending login is gone


def test_refresh_rotates_and_old_token_is_rejected(api_client):
    body = signup(api_client, "alex@example.com")
    old_refresh = body["meta"]["refresh_token"]
    response = api_client.post(
        f"{APP}/tokens/refresh", {"refresh_token": old_refresh}, format="json"
    )
    assert response.status_code == 200, response.json()
    new = response.json()["data"]
    assert new["access_token"]
    assert new["refresh_token"] != old_refresh
    response = api_client.post(
        f"{APP}/tokens/refresh", {"refresh_token": old_refresh}, format="json"
    )
    assert response.status_code == 400


def test_rapid_code_requests_from_one_ip_are_rate_limited(api_client):
    signup(api_client, "alex@example.com")
    statuses = [
        api_client.post(
            f"{APP}/auth/code/request", {"email": "alex@example.com"}, format="json"
        ).status_code
        for _ in range(21)
    ]
    # 20 code requests per minute per IP; then "too many login attempts" (400).
    # The per-email daily cap is tested in test_review_fixes.py.
    assert statuses == [401] * 20 + [400]

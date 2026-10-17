"""Regression tests for issues found in the final branch review."""

import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import APP, login, signup

pytestmark = pytest.mark.django_db


# I1: refresh must keep working for the 90-day lifetime, not die with the
# 2-week Django session.
def test_refresh_still_works_after_30_days(api_client):
    body = signup(api_client, "alex@example.com")
    later = timezone.now() + timedelta(days=30)
    with (
        patch("django.utils.timezone.now", return_value=later),
        patch("time.time", return_value=later.timestamp()),
    ):
        response = api_client.post(
            f"{APP}/tokens/refresh",
            {"refresh_token": body["meta"]["refresh_token"]},
            format="json",
        )
    assert response.status_code == 200, response.json()


# I2: users created outside allauth need a verified primary EmailAddress,
# otherwise code login stalls on "verify_email".
def test_create_user_adds_verified_primary_email_address():
    user = User.objects.create_user(email="Alex@Example.com")
    address = EmailAddress.objects.get(user=user)
    assert address.email == "alex@example.com"
    assert address.verified is True
    assert address.primary is True


def test_create_superuser_adds_verified_primary_email_address():
    admin = User.objects.create_superuser(
        email="boss@example.com", password="s3cret-pass!"
    )
    assert EmailAddress.objects.filter(user=admin, verified=True, primary=True).exists()


def test_user_created_with_manager_can_log_in_by_code(api_client):
    User.objects.create_user(email="alex@example.com")
    body = login(api_client, "alex@example.com")
    assert body["meta"]["access_token"]


def test_admin_add_user_adds_email_address_and_can_log_in(admin_client, api_client):
    admin_client.post(
        "/admin/accounts/user/add/", {"email": "new@example.com", "is_active": "on"}
    )
    assert EmailAddress.objects.filter(
        email="new@example.com", verified=True, primary=True
    ).exists()
    assert login(api_client, "new@example.com")["meta"]["access_token"]


def test_admin_change_page_email_is_read_only(admin_client):
    user = User.objects.create_user(email="alex@example.com")
    response = admin_client.get(f"/admin/accounts/user/{user.pk}/change/")
    assert response.status_code == 200
    assert b'name="email"' not in response.content


# I4: 6-digit codes need a longer rate-limit window than "3 per minute".
def test_code_requests_limited_to_30_per_day(api_client):
    User.objects.create_user(email="alex@example.com")
    start = time.time()
    statuses = []
    for i in range(31):
        with patch("time.time", return_value=start + i * 61):  # one per minute
            statuses.append(
                api_client.post(
                    f"{APP}/auth/code/request",
                    {"email": "alex@example.com"},
                    format="json",
                ).status_code
            )
    assert statuses[:30] == [401] * 30
    assert statuses[30] == 400

import pytest

from accounts.tests.helpers import signup

pytestmark = pytest.mark.django_db

ME = "/api/v1/me/"


def test_me_requires_token(api_client):
    assert api_client.get(ME).status_code == 401


def test_me_rejects_garbage_token(api_client):
    response = api_client.get(ME, HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert response.status_code == 401


def test_me_returns_email_and_trial(api_client):
    body = signup(api_client, "alex@example.com")
    access = body["meta"]["access_token"]
    response = api_client.get(ME, HTTP_AUTHORIZATION=f"Bearer {access}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alex@example.com"
    assert data["trial_active"] is True
    assert data["trial_ends_at"]

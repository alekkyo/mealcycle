import pytest

from accounts.tests.helpers import APP

pytestmark = pytest.mark.django_db


def test_config_endpoint_responds(api_client):
    response = api_client.get(f"{APP}/config")
    assert response.status_code == 200
    assert response.json()["data"]["account"]["login_by_code_enabled"] is True


def test_code_request_for_unknown_email_returns_400(api_client):
    response = api_client.post(
        f"{APP}/auth/code/request", {"email": "nobody@example.com"}, format="json"
    )
    assert response.status_code == 400


def test_signup_response_shape(api_client):
    response = api_client.post(
        f"{APP}/auth/signup", {"email": "new@example.com"}, format="json"
    )
    print(
        "SIGNUP", response.status_code, response.json()
    )  # pins shapes for later tasks
    assert response.status_code == 401  # pending: verify_email flow
    assert "session_token" in response.json()["meta"]

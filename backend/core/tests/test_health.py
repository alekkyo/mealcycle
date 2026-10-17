from unittest.mock import patch

import pytest
from django.db import OperationalError

pytestmark = pytest.mark.django_db

HEALTH_URL = "/api/v1/health/"


def test_health_ok_without_login(api_client):
    response = api_client.get(HEALTH_URL)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_down(api_client):
    with patch("core.views.connection") as mock_connection:
        mock_connection.ensure_connection.side_effect = OperationalError("db down")
        response = api_client.get(HEALTH_URL)
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}


def test_health_rejects_post(api_client):
    response = api_client.post(HEALTH_URL)
    assert response.status_code == 405

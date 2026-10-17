import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import jwt_secret


def test_jwt_secret_accepts_long_random_value(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)
    assert jwt_secret("JWT_SECRET_KEY") == "x" * 40


@pytest.mark.parametrize("value", ["change-me", "short", "a" * 31])
def test_jwt_secret_rejects_placeholder_or_short_value(monkeypatch, value):
    monkeypatch.setenv("JWT_SECRET_KEY", value)
    with pytest.raises(ImproperlyConfigured, match="JWT_SECRET_KEY"):
        jwt_secret("JWT_SECRET_KEY")

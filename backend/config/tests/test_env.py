import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import env_list, env_required


def test_env_required_returns_value(monkeypatch):
    monkeypatch.setenv("MEALCYCLE_TEST_VAR", "hello")
    assert env_required("MEALCYCLE_TEST_VAR") == "hello"


def test_env_required_raises_clear_error_when_missing(monkeypatch):
    monkeypatch.delenv("MEALCYCLE_TEST_VAR", raising=False)
    with pytest.raises(ImproperlyConfigured, match="MEALCYCLE_TEST_VAR"):
        env_required("MEALCYCLE_TEST_VAR")


def test_env_required_treats_empty_as_missing(monkeypatch):
    monkeypatch.setenv("MEALCYCLE_TEST_VAR", "")
    with pytest.raises(ImproperlyConfigured, match="MEALCYCLE_TEST_VAR"):
        env_required("MEALCYCLE_TEST_VAR")


def test_env_list_strips_spaces_and_drops_empties(monkeypatch):
    monkeypatch.setenv("MEALCYCLE_TEST_LIST", " localhost, 127.0.0.1,, ")
    assert env_list("MEALCYCLE_TEST_LIST") == ["localhost", "127.0.0.1"]


def test_env_list_returns_empty_list_when_unset(monkeypatch):
    monkeypatch.delenv("MEALCYCLE_TEST_LIST", raising=False)
    assert env_list("MEALCYCLE_TEST_LIST") == []

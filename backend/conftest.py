"""Shared pytest fixtures, discovered automatically by pytest."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def clear_cache():
    """Start every test with an empty cache.

    allauth's rate limits live in the cache, which (unlike the database) is not
    reset between tests, so one test's signups would rate-limit the next test.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """An unauthenticated DRF test client."""
    return APIClient()

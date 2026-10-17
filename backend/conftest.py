"""Shared pytest fixtures, discovered automatically by pytest."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """An unauthenticated DRF test client."""
    return APIClient()

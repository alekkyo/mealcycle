"""Helpers for reading configuration from environment variables."""

import os

from django.core.exceptions import ImproperlyConfigured


def env_required(name: str) -> str:
    """Return the variable's value, or fail loudly if it is missing or empty."""
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value


def env_list(name: str) -> list[str]:
    """Parse a comma-separated variable into a list, ignoring blanks."""
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]

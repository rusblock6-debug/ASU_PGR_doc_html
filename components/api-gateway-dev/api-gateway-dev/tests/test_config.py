"""Tests for gateway configuration validation."""

import pytest
from pydantic import ValidationError

from src.config import Settings


def _build_settings(service_config: dict[str, str]) -> Settings:
    """Create settings with one service for config validation tests."""
    return Settings(
        services={"test-service": service_config},
        auth={
            "url": "http://auth.example.com",
            "verify_endpoint": "/api/v1/verify",
        },
    )


def test_service_uses_default_path_pattern_when_omitted() -> None:
    """Service config falls back to default upstream path template."""
    settings = _build_settings({"url": "http://trip.example.com"})

    assert settings.services["test-service"].path_pattern == "/api/{version}/{path}"


def test_service_accepts_path_pattern_without_version_placeholder() -> None:
    """Service config accepts a pattern that only uses {path}."""
    settings = _build_settings(
        {
            "url": "http://trip.example.com",
            "path_pattern": "/api/{path}",
        },
    )

    assert settings.services["trip-service"].path_pattern == "/api/{path}"


def test_service_rejects_path_pattern_without_leading_slash() -> None:
    """Validation fails when path pattern does not start with slash."""
    with pytest.raises(ValidationError, match="path_pattern must start with '/'"):
        _build_settings(
            {
                "url": "http://trip.example.com",
                "path_pattern": "{path}",
            },
        )


def test_service_rejects_unknown_path_placeholder() -> None:
    """Validation fails for unsupported placeholders in pattern."""
    with pytest.raises(ValidationError, match=r"\{unknown\}"):
        _build_settings(
            {
                "url": "http://trip.example.com",
                "path_pattern": "/api/{unknown}/{path}",
            },
        )

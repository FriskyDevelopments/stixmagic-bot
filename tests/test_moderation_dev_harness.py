"""
Tests verifying that moderation/dev_harness.py cannot be enabled in a
production configuration (task 14).

Requirements covered:
  5.3 — moderation/dev_harness.py cannot be enabled in a production
        configuration — and a test asserts that, so the harness can never
        become a bypass.
"""

from __future__ import annotations

import os

import pytest

from moderation.dev_harness import (
    DevHarness,
    DevHarnessProductionError,
    MockGroup,
    MockUser,
    create_default_harness,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_group() -> MockGroup:
    """A minimal MockGroup for instantiation tests."""
    users = {
        1: MockUser(user_id=1, name="Test User", role="admin"),
    }
    return MockGroup(group_id=1, title="Test Group", users=users)


# ---------------------------------------------------------------------------
# 5.3 — DevHarness raises in production
# ---------------------------------------------------------------------------


class TestDevHarnessBlockedInProduction:
    """DevHarness cannot be instantiated when APP_ENV=production."""

    def test_raises_on_production_env(self, monkeypatch):
        """Direct instantiation with APP_ENV='production' raises."""
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(DevHarnessProductionError):
            DevHarness(group=_minimal_group())

    def test_raises_on_production_env_uppercase(self, monkeypatch):
        """The check is case-insensitive: 'PRODUCTION' also raises."""
        monkeypatch.setenv("APP_ENV", "PRODUCTION")
        with pytest.raises(DevHarnessProductionError):
            DevHarness(group=_minimal_group())

    def test_raises_on_production_env_whitespace(self, monkeypatch):
        """Leading/trailing whitespace is stripped before comparison."""
        monkeypatch.setenv("APP_ENV", "  Production  ")
        with pytest.raises(DevHarnessProductionError):
            DevHarness(group=_minimal_group())

    def test_create_default_harness_raises_in_production(self, monkeypatch):
        """The convenience factory also raises in production."""
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(DevHarnessProductionError):
            create_default_harness()

    def test_error_message_mentions_production(self, monkeypatch):
        """The error message clearly indicates why instantiation failed."""
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(DevHarnessProductionError, match="production"):
            DevHarness(group=_minimal_group())


# ---------------------------------------------------------------------------
# 5.3 — DevHarness allowed in non-production environments
# ---------------------------------------------------------------------------


class TestDevHarnessAllowedInDevelopment:
    """DevHarness works normally in development and test environments."""

    def test_allowed_in_development(self, monkeypatch):
        """APP_ENV='development' permits instantiation."""
        monkeypatch.setenv("APP_ENV", "development")
        harness = DevHarness(group=_minimal_group())
        assert harness is not None

    def test_allowed_when_env_unset(self, monkeypatch):
        """If APP_ENV is not set at all (test/CI default), instantiation works."""
        monkeypatch.delenv("APP_ENV", raising=False)
        harness = DevHarness(group=_minimal_group())
        assert harness is not None

    def test_allowed_when_env_empty(self, monkeypatch):
        """An empty APP_ENV is treated as non-production."""
        monkeypatch.setenv("APP_ENV", "")
        harness = DevHarness(group=_minimal_group())
        assert harness is not None

    def test_create_default_harness_works_in_development(self, monkeypatch):
        """The convenience factory works in development."""
        monkeypatch.setenv("APP_ENV", "development")
        harness = create_default_harness()
        assert harness is not None
        assert harness.group.title == "STIX Forge Lab"

    def test_harness_functional_after_creation(self, monkeypatch):
        """After successful creation, the harness is fully functional."""
        monkeypatch.setenv("APP_ENV", "development")
        harness = create_default_harness()
        result = harness.simulate_event({
            "actor_id": 3,
            "kind": "message",
            "text": "mute 10m",
            "target_id": 4,
            "target_role": "member",
        })
        assert result["result"]["ok"] is True
        assert result["result"]["outcome"] == "executed"

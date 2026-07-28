"""
Tests verifying that moderation fails closed (task 12).

Requirements covered:
  5.1 — Moderation fails closed: when a check errors or a backend is
        unreachable, content is not approved.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from moderation.host import ActionPolicy, ActionRequest, ModerationHost
from moderation.plugin import BridgePlugin, PluginEvent
from moderation.wizard import WizardInterpreter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_request(**overrides) -> ActionRequest:
    """Build a valid ActionRequest for the 'mute_user' action."""
    defaults = {
        "action": "mute_user",
        "actor_id": 100,
        "actor_role": "moderator",
        "target_id": 200,
        "target_role": "member",
    }
    defaults.update(overrides)
    return ActionRequest(**defaults)


def _host_with_broken_execute() -> ModerationHost:
    """Return a host whose _execute_action always raises (simulating backend error)."""
    host = ModerationHost()

    def _exploding_execute(request):
        raise RuntimeError("Backend unreachable: connection timed out")

    host._execute_action = _exploding_execute
    return host


def _host_with_broken_validation() -> ModerationHost:
    """Return a host whose _validate_role raises (simulating a check error)."""
    host = ModerationHost()

    def _exploding_validate(policy, request):
        raise ValueError("Unexpected null in role lookup")

    host._validate_role = _exploding_validate
    return host


# ---------------------------------------------------------------------------
# 5.1 — ModerationHost.process() fails closed on backend errors
# ---------------------------------------------------------------------------


class TestHostFailsClosed:
    """When internal checks or backends error, the host denies rather than approves."""

    def test_execute_action_exception_returns_denial(self):
        """If _execute_action raises (backend unreachable), result is ok=False."""
        host = _host_with_broken_execute()
        request = _valid_request()
        result = host.process(request)

        assert result.ok is False
        assert result.outcome == "error"
        assert "denied" in result.message.lower()
        # Must not have executed the action
        assert 200 not in host.active_mutes

    def test_execute_action_exception_does_not_raise(self):
        """The exception does not propagate to the caller."""
        host = _host_with_broken_execute()
        request = _valid_request()
        # Should not raise
        result = host.process(request)
        assert isinstance(result.ok, bool)

    def test_validate_role_exception_returns_denial(self):
        """If _validate_role raises (check error), result is ok=False."""
        host = _host_with_broken_validation()
        request = _valid_request()
        result = host.process(request)

        assert result.ok is False
        assert result.outcome == "error"
        assert "denied" in result.message.lower()

    def test_validate_role_exception_does_not_approve(self):
        """An error in validation must not accidentally approve the action."""
        host = _host_with_broken_validation()
        request = _valid_request()
        result = host.process(request)

        # The action must not have been executed
        assert 200 not in host.active_mutes
        assert result.ok is False

    def test_action_registry_key_error_fails_closed(self):
        """If the registry itself raises (corrupted state), result is denial."""
        host = ModerationHost()

        # Replace the registry with a dict that raises on get()
        class BrokenDict(dict):
            def get(self, key, default=None):
                raise KeyError("corrupted registry")

        host.action_registry = BrokenDict()
        request = _valid_request()
        result = host.process(request)

        assert result.ok is False
        assert result.outcome == "error"

    def test_error_result_includes_request_id(self):
        """Even on error, result has a valid request_id for audit trailing."""
        host = _host_with_broken_execute()
        request = _valid_request()
        result = host.process(request)

        assert result.request_id.startswith("mod-")

    def test_multiple_errors_increment_request_seq(self):
        """Successive errors still get unique request IDs."""
        host = _host_with_broken_execute()
        r1 = host.process(_valid_request())
        r2 = host.process(_valid_request())

        assert r1.request_id != r2.request_id

    def test_error_after_successful_request_still_denies(self):
        """A host that worked once can still fail closed on the next call."""
        host = ModerationHost()
        good_request = _valid_request()
        good_result = host.process(good_request)
        assert good_result.ok is True

        # Now break the backend
        host._execute_action = lambda r: (_ for _ in ()).throw(
            ConnectionError("lost connection")
        )
        bad_result = host.process(_valid_request())
        assert bad_result.ok is False
        assert bad_result.outcome == "error"


# ---------------------------------------------------------------------------
# 5.1 — BridgePlugin.handle_event() fails closed on errors
# ---------------------------------------------------------------------------


class TestPluginFailsClosed:
    """The bridge plugin layer also fails closed on unexpected errors."""

    def test_host_exception_propagation_caught(self):
        """If the host somehow raises past its own guard, the plugin still denies."""
        host = ModerationHost()

        # Bypass host's own fail-closed by patching process() itself
        def _exploding_process(request):
            raise RuntimeError("total failure")

        host.process = _exploding_process

        plugin = BridgePlugin(host, WizardInterpreter())
        event = PluginEvent(
            kind="admin_action",
            actor_id=1,
            actor_role="admin",
            target_id=2,
            target_role="member",
            metadata={"action": "mute_user"},
        )
        result = plugin.handle_event(event)

        assert result.ok is False
        assert result.outcome == "error"
        assert "denied" in result.message.lower()

    def test_wizard_parse_exception_caught(self):
        """If WizardInterpreter.parse raises, the plugin fails closed."""
        host = ModerationHost()
        wizard = WizardInterpreter()
        wizard.parse = lambda text: (_ for _ in ()).throw(
            TypeError("unexpected None")
        )

        plugin = BridgePlugin(host, wizard)
        event = PluginEvent(
            kind="message",
            actor_id=1,
            actor_role="admin",
            text="mute 10m",
            target_id=2,
            target_role="member",
        )
        result = plugin.handle_event(event)

        assert result.ok is False
        assert result.outcome == "error"

    def test_plugin_error_never_returns_ok_true(self):
        """Under no error scenario should the plugin return ok=True."""
        host = ModerationHost()

        # Break _to_action_request indirectly by passing malformed event metadata
        # that causes the internal method to blow up
        def _exploding_to_action_request(event):
            raise AttributeError("missing attribute in event")

        plugin = BridgePlugin(host, WizardInterpreter())
        plugin._to_action_request = _exploding_to_action_request

        event = PluginEvent(
            kind="admin_action",
            actor_id=1,
            actor_role="admin",
            target_id=2,
            target_role="member",
            metadata={"action": "ban_user"},
        )
        result = plugin.handle_event(event)

        assert result.ok is False

    def test_backend_unreachable_simulation(self):
        """
        Simulate a network-unreachable backend: the host's execution layer
        raises a ConnectionError. The entire chain must deny.
        """
        host = ModerationHost()
        host._execute_action = lambda r: (_ for _ in ()).throw(
            ConnectionError("Connection refused")
        )

        plugin = BridgePlugin(host, WizardInterpreter())
        event = PluginEvent(
            kind="admin_action",
            actor_id=1,
            actor_role="admin",
            target_id=2,
            target_role="member",
            metadata={"action": "mute_user"},
        )
        result = plugin.handle_event(event)

        assert result.ok is False
        assert "denied" in result.message.lower()

    def test_timeout_error_fails_closed(self):
        """A TimeoutError (backend slow/dead) results in denial."""
        host = ModerationHost()
        host._execute_action = lambda r: (_ for _ in ()).throw(
            TimeoutError("request timed out")
        )

        plugin = BridgePlugin(host, WizardInterpreter())
        event = PluginEvent(
            kind="admin_action",
            actor_id=1,
            actor_role="moderator",
            target_id=2,
            target_role="member",
            metadata={"action": "warn_user"},
        )
        result = plugin.handle_event(event)

        assert result.ok is False
        assert result.outcome == "error"

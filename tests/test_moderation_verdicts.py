"""
Tests verifying that each documented moderation verdict is produced by
the condition described (task 13).

Requirements covered:
  5.2 — Each documented verdict is produced by the condition described.
"""

from __future__ import annotations

import pytest

from moderation.host import ActionPolicy, ActionRequest, ModerationHost, default_action_registry
from moderation.plugin import BridgePlugin, PluginEvent
from moderation.wizard import WizardInterpreter, WizardIntent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _host() -> ModerationHost:
    return ModerationHost()


def _request(**overrides) -> ActionRequest:
    """Build a valid ActionRequest with sensible defaults."""
    defaults = {
        "action": "mute_user",
        "actor_id": 100,
        "actor_role": "moderator",
        "target_id": 200,
        "target_role": "member",
    }
    defaults.update(overrides)
    return ActionRequest(**defaults)


# ---------------------------------------------------------------------------
# Verdict: "executed" — the action is approved and side effects applied
# ---------------------------------------------------------------------------


class TestVerdictExecuted:
    """A properly authorised request produces outcome='executed' and ok=True."""

    def test_mute_user_executed(self):
        host = _host()
        result = host.process(_request(action="mute_user"))
        assert result.ok is True
        assert result.outcome == "executed"
        assert 200 in host.active_mutes

    def test_warn_user_executed(self):
        host = _host()
        result = host.process(_request(action="warn_user"))
        assert result.ok is True
        assert result.outcome == "executed"
        assert host.active_warnings[200] == 1

    def test_delete_message_executed(self):
        host = _host()
        result = host.process(
            _request(
                action="delete_message",
                metadata={"message_id": "msg-42"},
            )
        )
        assert result.ok is True
        assert result.outcome == "executed"
        assert "msg-42" in host.deleted_messages

    def test_pin_message_executed(self):
        host = _host()
        result = host.process(
            _request(
                action="pin_message",
                metadata={"message_id": "msg-99"},
            )
        )
        assert result.ok is True
        assert result.outcome == "executed"
        assert "msg-99" in host.pinned_messages

    def test_ban_user_executed_with_confirmation(self):
        host = _host()
        result = host.process(
            _request(
                action="ban_user",
                actor_role="admin",
                confirmation_token="CONFIRMED",
            )
        )
        assert result.ok is True
        assert result.outcome == "executed"
        assert 200 in host.banned_users

    def test_executed_result_fields(self):
        host = _host()
        result = host.process(_request(action="warn_user"))
        assert result.request_id.startswith("mod-")
        assert result.action == "warn_user"
        assert result.actor_id == 100
        assert result.target_id == 200
        assert result.requires_confirmation is False


# ---------------------------------------------------------------------------
# Verdict: "unknown_action" — action not in registry
# ---------------------------------------------------------------------------


class TestVerdictUnknownAction:
    """An action not registered in the policy produces 'unknown_action'."""

    def test_unregistered_action_rejected(self):
        host = _host()
        result = host.process(_request(action="nuke_chat"))
        assert result.ok is False
        assert result.outcome == "unknown_action"
        assert "not registered" in result.message.lower()

    def test_empty_action_string_rejected(self):
        host = _host()
        result = host.process(_request(action=""))
        assert result.ok is False
        assert result.outcome == "unknown_action"

    def test_case_sensitive_action_lookup(self):
        """Action lookup is exact-match; 'Mute_User' is not 'mute_user'."""
        host = _host()
        result = host.process(_request(action="Mute_User"))
        assert result.ok is False
        assert result.outcome == "unknown_action"


# ---------------------------------------------------------------------------
# Verdict: "forbidden" — actor role insufficient
# ---------------------------------------------------------------------------


class TestVerdictForbidden:
    """An actor whose role level is below the policy minimum gets 'forbidden'."""

    def test_member_cannot_mute(self):
        host = _host()
        result = host.process(_request(actor_role="member"))
        assert result.ok is False
        assert result.outcome == "forbidden"

    def test_moderator_cannot_ban(self):
        host = _host()
        result = host.process(_request(action="ban_user", actor_role="moderator"))
        assert result.ok is False
        assert result.outcome == "forbidden"

    def test_unknown_actor_role_forbidden(self):
        """An unrecognised role string gets level -1, below any policy."""
        host = _host()
        result = host.process(_request(actor_role="guest"))
        assert result.ok is False
        assert result.outcome == "forbidden"

    def test_forbidden_message_describes_mismatch(self):
        host = _host()
        result = host.process(_request(actor_role="member"))
        assert "member" in result.message
        assert "mute_user" in result.message


# ---------------------------------------------------------------------------
# Verdict: "invalid_target" — target validation failure
# ---------------------------------------------------------------------------


class TestVerdictInvalidTarget:
    """Target validation failures produce 'invalid_target'."""

    def test_missing_target_id(self):
        host = _host()
        result = host.process(_request(target_id=None))
        assert result.ok is False
        assert result.outcome == "invalid_target"
        assert "required" in result.message.lower()

    def test_missing_target_role(self):
        host = _host()
        result = host.process(_request(target_role=None))
        assert result.ok is False
        assert result.outcome == "invalid_target"
        assert "required" in result.message.lower()

    def test_target_role_not_allowed_by_policy(self):
        """mute_user only allows targeting 'member'; targeting 'admin' fails."""
        host = _host()
        result = host.process(_request(action="mute_user", target_role="admin"))
        assert result.ok is False
        assert result.outcome == "invalid_target"
        assert "cannot be targeted" in result.message.lower()

    def test_cannot_target_equal_role(self):
        """A moderator cannot mute another moderator (equal level)."""
        host = _host()
        # delete_message allows targeting moderators, so use that
        result = host.process(
            _request(
                action="delete_message",
                actor_role="moderator",
                target_role="moderator",
                metadata={"message_id": "msg-1"},
            )
        )
        assert result.ok is False
        assert result.outcome == "invalid_target"
        assert "equal or higher" in result.message.lower()

    def test_cannot_target_higher_role(self):
        """A moderator cannot delete a message from an admin."""
        host = _host()
        result = host.process(
            _request(
                action="delete_message",
                actor_role="moderator",
                target_role="admin",
                metadata={"message_id": "msg-1"},
            )
        )
        assert result.ok is False
        assert result.outcome == "invalid_target"

    def test_admin_can_target_moderator_for_ban(self):
        """ban_user allows moderators as targets; admin > moderator in level."""
        host = _host()
        result = host.process(
            _request(
                action="ban_user",
                actor_role="admin",
                target_role="moderator",
                confirmation_token="CONFIRMED",
            )
        )
        assert result.ok is True
        assert result.outcome == "executed"


# ---------------------------------------------------------------------------
# Verdict: "confirmation_required" — action needs explicit confirmation
# ---------------------------------------------------------------------------


class TestVerdictConfirmationRequired:
    """Actions with requires_confirmation=True deny without the token."""

    def test_ban_without_confirmation_denied(self):
        host = _host()
        result = host.process(
            _request(
                action="ban_user",
                actor_role="admin",
                confirmation_token=None,
            )
        )
        assert result.ok is False
        assert result.outcome == "confirmation_required"
        assert result.requires_confirmation is True

    def test_wrong_confirmation_token_denied(self):
        host = _host()
        result = host.process(
            _request(
                action="ban_user",
                actor_role="admin",
                confirmation_token="WRONG_TOKEN",
            )
        )
        assert result.ok is False
        assert result.outcome == "confirmation_required"

    def test_confirmation_not_required_for_mute(self):
        """mute_user does not require confirmation per policy."""
        host = _host()
        result = host.process(_request(action="mute_user", confirmation_token=None))
        assert result.ok is True
        assert result.outcome == "executed"

    def test_confirmed_ban_succeeds(self):
        host = _host()
        result = host.process(
            _request(
                action="ban_user",
                actor_role="admin",
                confirmation_token="CONFIRMED",
            )
        )
        assert result.ok is True
        assert result.outcome == "executed"


# ---------------------------------------------------------------------------
# Verdict: "ignored" — plugin event does not map to moderation action
# ---------------------------------------------------------------------------


class TestVerdictIgnored:
    """Events that don't resolve to an action produce 'ignored' at plugin level."""

    def test_empty_text_message_ignored(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
        event = PluginEvent(
            kind="message",
            actor_id=1,
            actor_role="moderator",
            text="",
            target_id=2,
            target_role="member",
        )
        result = plugin.handle_event(event)
        assert result.ok is False
        assert result.outcome == "ignored"

    def test_unrecognised_text_ignored(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
        event = PluginEvent(
            kind="message",
            actor_id=1,
            actor_role="moderator",
            text="hello world",
            target_id=2,
            target_role="member",
        )
        result = plugin.handle_event(event)
        assert result.ok is False
        assert result.outcome == "ignored"

    def test_admin_action_without_action_metadata_ignored(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
        event = PluginEvent(
            kind="admin_action",
            actor_id=1,
            actor_role="admin",
            target_id=2,
            target_role="member",
            metadata={},  # no "action" key
        )
        result = plugin.handle_event(event)
        assert result.ok is False
        assert result.outcome == "ignored"

    def test_unknown_event_kind_ignored(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
        event = PluginEvent(
            kind="unknown_kind",
            actor_id=1,
            actor_role="admin",
            target_id=2,
            target_role="member",
        )
        result = plugin.handle_event(event)
        assert result.ok is False
        assert result.outcome == "ignored"


# ---------------------------------------------------------------------------
# WizardInterpreter verdicts — intent resolution
# ---------------------------------------------------------------------------


class TestWizardVerdicts:
    """The wizard produces the correct intent for each documented shortcut."""

    def test_mute_default_duration(self):
        intent = WizardInterpreter().parse("mute")
        assert intent.action == "mute_user"
        assert intent.duration_seconds == 600  # 10 min default

    def test_mute_minutes(self):
        intent = WizardInterpreter().parse("mute 5m")
        assert intent.action == "mute_user"
        assert intent.duration_seconds == 300

    def test_mute_hours(self):
        intent = WizardInterpreter().parse("mute 2h")
        assert intent.action == "mute_user"
        assert intent.duration_seconds == 7200

    def test_mute_numeric_seconds(self):
        intent = WizardInterpreter().parse("mute 120")
        assert intent.action == "mute_user"
        assert intent.duration_seconds == 120

    def test_warn_user_shortcut(self):
        intent = WizardInterpreter().parse("warn user")
        assert intent.action == "warn_user"

    def test_handle_this_shortcut(self):
        intent = WizardInterpreter().parse("handle this")
        assert intent.action == "warn_user"

    def test_ban_user_shortcut(self):
        intent = WizardInterpreter().parse("ban user")
        assert intent.action == "ban_user"

    def test_delete_this_shortcut(self):
        intent = WizardInterpreter().parse("delete this")
        assert intent.action == "delete_message"

    def test_pin_this_shortcut(self):
        intent = WizardInterpreter().parse("pin this")
        assert intent.action == "pin_message"

    def test_unrecognised_text_no_action(self):
        intent = WizardInterpreter().parse("just chatting")
        assert intent.action is None
        assert intent.confidence < 0.5

    def test_empty_text_no_action(self):
        intent = WizardInterpreter().parse("")
        assert intent.action is None
        assert intent.confidence == 0.0

    def test_none_text_no_action(self):
        intent = WizardInterpreter().parse(None)
        assert intent.action is None

    def test_case_insensitive_shortcuts(self):
        intent = WizardInterpreter().parse("HANDLE THIS")
        assert intent.action == "warn_user"

    def test_shortcut_as_substring(self):
        """Shortcuts match if they appear anywhere in the normalised text."""
        intent = WizardInterpreter().parse("please handle this now")
        assert intent.action == "warn_user"


# ---------------------------------------------------------------------------
# End-to-end: event → wizard → host → verdict
# ---------------------------------------------------------------------------


class TestEndToEndVerdicts:
    """Full pipeline from plugin event through wizard to host verdict."""

    def test_message_event_mute_executed(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
        event = PluginEvent(
            kind="message",
            actor_id=1,
            actor_role="moderator",
            text="mute 15m",
            target_id=2,
            target_role="member",
        )
        result = plugin.handle_event(event)
        assert result.ok is True
        assert result.outcome == "executed"
        assert plugin.host.active_mutes[2] == 900

    def test_admin_action_ban_requires_confirmation(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
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
        assert result.outcome == "confirmation_required"

    def test_admin_action_ban_confirmed(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
        event = PluginEvent(
            kind="admin_action",
            actor_id=1,
            actor_role="admin",
            target_id=2,
            target_role="member",
            confirmation_token="CONFIRMED",
            metadata={"action": "ban_user"},
        )
        result = plugin.handle_event(event)
        assert result.ok is True
        assert result.outcome == "executed"

    def test_member_message_mute_forbidden(self):
        plugin = BridgePlugin(ModerationHost(), WizardInterpreter())
        event = PluginEvent(
            kind="message",
            actor_id=4,
            actor_role="member",
            text="mute 10m",
            target_id=5,
            target_role="member",
        )
        result = plugin.handle_event(event)
        assert result.ok is False
        assert result.outcome == "forbidden"

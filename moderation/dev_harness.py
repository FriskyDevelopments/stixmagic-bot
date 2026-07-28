from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any

from .host import ModerationHost
from .plugin import BridgePlugin, PluginEvent
from .wizard import WizardInterpreter


class DevHarnessProductionError(RuntimeError):
    """Raised when DevHarness is instantiated in a production environment."""


@dataclass(slots=True)
class MockUser:
    user_id: int
    name: str
    role: str


@dataclass(slots=True)
class MockGroup:
    group_id: int
    title: str
    users: dict[int, MockUser] = field(default_factory=dict)


class DevHarness:
    """Dev/test simulator with replayable event history.

    Cannot be instantiated when APP_ENV is ``"production"``.  Raises
    :class:`DevHarnessProductionError` to prevent the harness from ever
    acting as a moderation bypass in a live environment.
    """

    def __init__(self, group: MockGroup, host: ModerationHost | None = None):
        app_env = os.environ.get("APP_ENV", "").strip().lower()
        if app_env == "production":
            raise DevHarnessProductionError(
                "DevHarness cannot be enabled in a production environment "
                "(APP_ENV='production')."
            )

        self.group = group
        self.host = host or ModerationHost()
        self.plugin = BridgePlugin(self.host, WizardInterpreter())
        self.replay_buffer: list[dict[str, Any]] = []

    def simulate_event(self, payload: dict[str, Any]):
        actor_id = int(payload["actor_id"])
        target_id = int(payload.get("target_id")) if payload.get("target_id") is not None else None

        actor = self.group.users.get(actor_id)
        if not actor:
            raise ValueError(f"Unknown actor_id {actor_id}")

        target = self.group.users.get(target_id) if target_id is not None else None

        event = PluginEvent(
            kind=payload.get("kind", "message"),
            actor_id=actor.user_id,
            actor_role=actor.role,
            text=payload.get("text"),
            target_id=target.user_id if target else target_id,
            target_role=target.role if target else payload.get("target_role"),
            message_id=payload.get("message_id"),
            confirmation_token=payload.get("confirmation_token"),
            metadata=payload.get("metadata", {}),
        )
        result = self.plugin.handle_event(event)

        replay_item = {
            "payload": payload,
            "result": asdict(result),
        }
        self.replay_buffer.append(replay_item)
        return replay_item

    def state(self) -> dict[str, Any]:
        return {
            "group": {
                "group_id": self.group.group_id,
                "title": self.group.title,
                "users": [asdict(u) for u in self.group.users.values()],
            },
            "host": self.host.as_dict(),
            "plugin": self.plugin.as_dict(),
            "replay": self.replay_buffer,
        }


def create_default_harness() -> DevHarness:
    users = {
        1: MockUser(user_id=1, name="Owner Owl", role="owner"),
        2: MockUser(user_id=2, name="Admin Fox", role="admin"),
        3: MockUser(user_id=3, name="Mod Lynx", role="moderator"),
        4: MockUser(user_id=4, name="Member Bee", role="member"),
        5: MockUser(user_id=5, name="Member Bat", role="member"),
    }
    group = MockGroup(group_id=101, title="STIX Forge Lab", users=users)
    return DevHarness(group=group)

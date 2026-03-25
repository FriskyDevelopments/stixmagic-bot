from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


ROLE_LEVEL = {
    "member": 0,
    "moderator": 1,
    "admin": 2,
    "owner": 3,
}


@dataclass(slots=True)
class ActionPolicy:
    action: str
    required_role: str
    requires_confirmation: bool = False
    allowed_target_roles: set[str] = field(default_factory=lambda: {"member"})


@dataclass(slots=True)
class ActionRequest:
    action: str
    actor_id: int
    actor_role: str
    target_id: int | None = None
    target_role: str | None = None
    reason: str | None = None
    duration_seconds: int | None = None
    ui_source: str = "wizard"
    confirmation_token: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AuditEntry:
    request_id: str
    at: str
    action: str
    actor_id: int
    actor_role: str
    target_id: int | None
    target_role: str | None
    outcome: str
    message: str
    reason: str | None
    metadata: dict[str, Any]


@dataclass(slots=True)
class HostResult:
    ok: bool
    request_id: str
    outcome: str
    message: str
    action: str
    actor_id: int
    target_id: int | None
    requires_confirmation: bool = False


class ModerationHost:
    """GroupHelp-style moderation host with strict authority controls."""

    def __init__(self, action_registry: dict[str, ActionPolicy] | None = None):
        self.action_registry = action_registry or default_action_registry()
        self.audit_log: list[AuditEntry] = []
        self.active_mutes: dict[int, int] = {}
        self.active_warnings: dict[int, int] = {}
        self.banned_users: set[int] = set()
        self.deleted_messages: list[str] = []
        self.pinned_messages: set[str] = set()
        self._request_seq = 0

    def process(self, request: ActionRequest) -> HostResult:
        self._request_seq += 1
        request_id = f"mod-{self._request_seq:06d}"

        policy = self.action_registry.get(request.action)
        if not policy:
            return self._reject(request_id, request, "unknown_action", "Action is not registered")

        role_error = self._validate_role(policy, request)
        if role_error:
            return self._reject(request_id, request, "forbidden", role_error)

        target_error = self._validate_target(policy, request)
        if target_error:
            return self._reject(request_id, request, "invalid_target", target_error)

        if policy.requires_confirmation and request.confirmation_token != "CONFIRMED":
            return self._reject(
                request_id,
                request,
                "confirmation_required",
                "This action needs explicit confirmation",
                requires_confirmation=True,
            )

        message = self._execute_action(request)
        result = HostResult(
            ok=True,
            request_id=request_id,
            outcome="executed",
            message=message,
            action=request.action,
            actor_id=request.actor_id,
            target_id=request.target_id,
        )
        self._log(request_id, request, result.outcome, result.message)
        return result

    def _validate_role(self, policy: ActionPolicy, request: ActionRequest) -> str | None:
        actor_level = ROLE_LEVEL.get(request.actor_role, -1)
        required_level = ROLE_LEVEL.get(policy.required_role, 999)
        if actor_level < required_level:
            return f"Role '{request.actor_role}' cannot run '{request.action}'"
        return None

    def _validate_target(self, policy: ActionPolicy, request: ActionRequest) -> str | None:
        if request.target_id is None:
            return "Target user/message is required"
        if request.target_role is None:
            return "Target role is required"

        if request.target_role not in policy.allowed_target_roles:
            return f"Target role '{request.target_role}' cannot be targeted by '{request.action}'"

        actor_level = ROLE_LEVEL.get(request.actor_role, -1)
        target_level = ROLE_LEVEL.get(request.target_role, -1)
        if target_level >= actor_level:
            return "Cannot act on equal or higher role"

        return None

    def _execute_action(self, request: ActionRequest) -> str:
        action = request.action
        target_id = request.target_id
        if action == "ban_user":
            self.banned_users.add(target_id)
            return f"User {target_id} banned"
        if action == "mute_user":
            duration = request.duration_seconds or 600
            self.active_mutes[target_id] = duration
            return f"User {target_id} muted for {duration}s"
        if action == "warn_user":
            self.active_warnings[target_id] = self.active_warnings.get(target_id, 0) + 1
            return f"User {target_id} warned (total {self.active_warnings[target_id]})"
        if action == "delete_message":
            message_id = str(request.metadata.get("message_id") or "unknown")
            self.deleted_messages.append(message_id)
            return f"Message {message_id} deleted"
        if action == "pin_message":
            message_id = str(request.metadata.get("message_id") or "unknown")
            self.pinned_messages.add(message_id)
            return f"Message {message_id} pinned"
        return "Action executed"

    def _reject(
        self,
        request_id: str,
        request: ActionRequest,
        outcome: str,
        message: str,
        requires_confirmation: bool = False,
    ) -> HostResult:
        result = HostResult(
            ok=False,
            request_id=request_id,
            outcome=outcome,
            message=message,
            action=request.action,
            actor_id=request.actor_id,
            target_id=request.target_id,
            requires_confirmation=requires_confirmation,
        )
        self._log(request_id, request, outcome, message)
        return result

    def _log(self, request_id: str, request: ActionRequest, outcome: str, message: str):
        self.audit_log.append(
            AuditEntry(
                request_id=request_id,
                at=datetime.now(timezone.utc).isoformat(),
                action=request.action,
                actor_id=request.actor_id,
                actor_role=request.actor_role,
                target_id=request.target_id,
                target_role=request.target_role,
                outcome=outcome,
                message=message,
                reason=request.reason,
                metadata={"ui_source": request.ui_source, **request.metadata},
            )
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy": [
                {
                    "action": p.action,
                    "required_role": p.required_role,
                    "requires_confirmation": p.requires_confirmation,
                    "allowed_target_roles": sorted(p.allowed_target_roles),
                }
                for p in self.action_registry.values()
            ],
            "audit_log": [asdict(entry) for entry in self.audit_log],
            "state": {
                "banned_users": sorted(self.banned_users),
                "active_mutes": self.active_mutes,
                "warnings": self.active_warnings,
                "deleted_messages": self.deleted_messages,
                "pinned_messages": sorted(self.pinned_messages),
            },
        }


def default_action_registry() -> dict[str, ActionPolicy]:
    return {
        "ban_user": ActionPolicy(
            action="ban_user",
            required_role="admin",
            requires_confirmation=True,
            allowed_target_roles={"member", "moderator"},
        ),
        "mute_user": ActionPolicy(
            action="mute_user",
            required_role="moderator",
            requires_confirmation=False,
            allowed_target_roles={"member"},
        ),
        "warn_user": ActionPolicy(
            action="warn_user",
            required_role="moderator",
            requires_confirmation=False,
            allowed_target_roles={"member"},
        ),
        "delete_message": ActionPolicy(
            action="delete_message",
            required_role="moderator",
            requires_confirmation=False,
            allowed_target_roles={"member", "moderator"},
        ),
        "pin_message": ActionPolicy(
            action="pin_message",
            required_role="moderator",
            requires_confirmation=False,
            allowed_target_roles={"member", "moderator", "admin"},
        ),
    }

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .host import ActionRequest, HostResult, ModerationHost
from .wizard import WizardInterpreter


@dataclass(slots=True)
class PluginEvent:
    kind: str
    actor_id: int
    actor_role: str
    text: str | None = None
    target_id: int | None = None
    target_role: str | None = None
    message_id: str | None = None
    confirmation_token: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BridgePlugin:
    """Bridge layer: events -> normalized action request -> host execution."""

    def __init__(self, host: ModerationHost, wizard: WizardInterpreter | None = None):
        self.host = host
        self.wizard = wizard or WizardInterpreter()
        self.event_log: list[dict[str, Any]] = []

    def handle_event(self, event: PluginEvent) -> HostResult:
        try:
            return self._handle_event_inner(event)
        except Exception as exc:
            # Fail closed: any unexpected error results in denial, never approval.
            return HostResult(
                ok=False,
                request_id="plugin-error",
                outcome="error",
                message=f"Internal error — action denied: {exc}",
                action=getattr(event, "kind", "unknown"),
                actor_id=event.actor_id,
                target_id=event.target_id,
            )

    def _handle_event_inner(self, event: PluginEvent) -> HostResult:
        request = self._to_action_request(event)
        if not request:
            return HostResult(
                ok=False,
                request_id="plugin-ignored",
                outcome="ignored",
                message="Event did not map to a moderation action",
                action="none",
                actor_id=event.actor_id,
                target_id=event.target_id,
            )

        result = self.host.process(request)
        self.event_log.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "event": asdict(event),
                "request": asdict(request),
                "result": asdict(result),
            }
        )
        return result

    def _to_action_request(self, event: PluginEvent) -> ActionRequest | None:
        action = None
        duration = None

        if event.kind == "admin_action":
            action = event.metadata.get("action")
            duration = event.metadata.get("duration_seconds")
        elif event.kind in {"reply", "message"}:
            intent = self.wizard.parse(event.text or "")
            action = intent.action
            duration = intent.duration_seconds

        if not action:
            return None

        return ActionRequest(
            action=action,
            actor_id=event.actor_id,
            actor_role=event.actor_role,
            target_id=event.target_id,
            target_role=event.target_role,
            duration_seconds=duration,
            reason=event.metadata.get("reason"),
            ui_source=event.kind,
            confirmation_token=event.confirmation_token,
            metadata={
                "message_id": event.message_id,
                **event.metadata,
            },
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_log": self.event_log,
            "event_count": len(self.event_log),
        }

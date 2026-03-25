"""Shared session primitives for wizard and trigger state."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from core.contracts import SessionStore
from core.types import UserSessionContext


@dataclass(slots=True)
class WizardState:
    """Normalized wizard state tracked in shared core flows."""

    flow_name: str
    step: str
    payload: dict[str, Any] = field(default_factory=dict)


class InMemorySessionStore(SessionStore):
    """Simple in-memory session storage for local/testing use."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def get(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._store.get(session_id, {}))

    def set(self, session_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._store[session_id] = dict(data)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)


def build_session_id(user: UserSessionContext, platform: str) -> str:
    """Build deterministic session IDs shared by adapters."""

    return f"{platform}:{user.user_id}:{user.session_id}"

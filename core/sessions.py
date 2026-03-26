"""Shared session primitives for wizard and trigger state."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
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
    """Simple in-memory session storage for local/testing use.

    Implements both sync (SessionStore) and async (AsyncSessionStore) interfaces.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def sync_get(self, session_id: str) -> dict[str, Any]:
        """Synchronous get implementation."""
        with self._lock:
            return deepcopy(self._store.get(session_id, {}))

    def sync_set(self, session_id: str, data: dict[str, Any]) -> None:
        """Synchronous set implementation."""
        with self._lock:
            self._store[session_id] = deepcopy(data)

    def sync_clear(self, session_id: str) -> None:
        """Synchronous clear implementation."""
        with self._lock:
            self._store.pop(session_id, None)

    # Async interface (AsyncSessionStore protocol) - delegates to sync implementations using asyncio.to_thread
    async def get(self, session_id: str) -> dict[str, Any]:
        """Async get that delegates to synchronous implementation."""
        return await asyncio.to_thread(self.sync_get, session_id)

    async def set(self, session_id: str, data: dict[str, Any]) -> None:
        """Async set that delegates to synchronous implementation."""
        await asyncio.to_thread(self.sync_set, session_id, data)

    async def clear(self, session_id: str) -> None:
        """Async clear that delegates to synchronous implementation."""
        await asyncio.to_thread(self.sync_clear, session_id)


def build_session_id(user: UserSessionContext, platform: str) -> str:
    """Build deterministic collision-safe session IDs shared by adapters."""

    # Use JSON serialization of components and hash for collision-safe deterministic key
    components = [platform, str(user.user_id), user.session_id]
    serialized = json.dumps(components, sort_keys=True)
    digest = sha256(serialized.encode('utf-8')).hexdigest()
    return f"session_{digest}"
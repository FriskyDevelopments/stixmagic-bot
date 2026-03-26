"""Core contracts for platform adapters and extension points."""

from __future__ import annotations

from typing import Any, Protocol

from .capabilities import PlatformCapabilities
from .types import (
    PackGenerationRequest,
    PackGenerationResult,
    PlatformEventContext,
    ReactionRenderInput,
    ReactionRenderResult,
    StickerGenerationInput,
    StickerGenerationOutput,
    UserSessionContext,
)


class MediaNormalizer(Protocol):
    """Normalizes arbitrary media into sticker-safe outputs."""

    async def normalize_sticker(
        self,
        sticker_input: StickerGenerationInput,
        *,
        capabilities: PlatformCapabilities,
    ) -> StickerGenerationOutput:
        ...


class TriggerExecutor(Protocol):
    """Entry point for trigger/command execution from platform events."""

    async def execute_trigger(
        self,
        event: PlatformEventContext,
        session: UserSessionContext,
    ) -> Any:
        ...


class FlowRenderer(Protocol):
    """Adapter hook for rendering wizard/flow steps and prompts."""

    async def render_flow_step(
        self,
        *,
        flow_name: str,
        step: str,
        payload: dict[str, Any],
        event: PlatformEventContext,
        session: UserSessionContext,
    ) -> Any:
        ...


class PlatformAdapter(Protocol):
    """Adapter contract implemented by Telegram/Discord integrations."""

    @property
    def platform_name(self) -> str:
        ...

    @property
    def capabilities(self) -> PlatformCapabilities:
        ...

    async def publish_pack_result(
        self,
        event: PlatformEventContext,
        result: PackGenerationResult,
    ) -> Any:
        ...

    async def publish_error(
        self,
        event: PlatformEventContext,
        message: str,
    ) -> Any:
        ...


class PackFormatter(Protocol):
    """Optional capability-aware formatter for platform-specific output shaping."""

    async def format_pack_result(
        self,
        result: PackGenerationResult,
        *,
        capabilities: PlatformCapabilities,
    ) -> PackGenerationResult:
        ...


class SessionStore(Protocol):
    """Contract for wizard/session state persistence."""

    def get(self, session_id: str) -> dict[str, Any]:
        ...

    def set(self, session_id: str, data: dict[str, Any]) -> None:
        ...

    def clear(self, session_id: str) -> None:
        ...


class AsyncSessionStore(Protocol):
    """Async contract for wizard/session state persistence."""

    async def get(self, session_id: str) -> dict[str, Any]:
        ...

    async def set(self, session_id: str, data: dict[str, Any]) -> None:
        ...

    async def clear(self, session_id: str) -> None:
        ...


class SupportsPackGeneration(Protocol):
    """Shared contract for core pack generation entry."""

    async def generate_pack(
        self,
        request: PackGenerationRequest,
        *,
        capabilities: PlatformCapabilities,
    ) -> PackGenerationResult:
        ...


class StixCoreContract(Protocol):
    """Legacy contract for platform adapters using the simpler generation API."""

    async def generate_pack(self, payload: Any) -> Any:
        """Convert incoming media into a platform-ready sticker payload."""

    async def generate_reactions(self, payload: ReactionRenderInput) -> ReactionRenderResult:
        """Render a normalized reaction + metadata text block for platform adapters."""
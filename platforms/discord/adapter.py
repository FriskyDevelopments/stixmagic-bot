"""Thin Discord adapter implementing shared platform contracts."""

from __future__ import annotations

from core.capabilities import DISCORD_CAPABILITIES, PlatformCapabilities
from core.types import PackGenerationResult, PlatformEventContext


class DiscordPlatformAdapter:
    """Adapter boundary for Discord-specific IO concerns."""

    @property
    def platform_name(self) -> str:
        return "discord"

    @property
    def capabilities(self) -> PlatformCapabilities:
        return DISCORD_CAPABILITIES

    async def publish_pack_result(
        self,
        event: PlatformEventContext,
        result: PackGenerationResult,
    ) -> dict[str, str | int | None]:
        return {
            "platform": self.platform_name,
            "chat_id": event.chat_id,
            "pack_id": result.pack_id,
            "status": "ok",
        }

    async def publish_error(
        self,
        event: PlatformEventContext,
        message: str,
    ) -> dict[str, str | int | None]:
        return {
            "platform": self.platform_name,
            "chat_id": event.chat_id,
            "status": "error",
            "message": message,
        }

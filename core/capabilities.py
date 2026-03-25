"""Platform capability model for adapter-aware behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformCapabilities:
    """Capabilities exposed by a platform adapter."""

    supports_native_sticker_packs: bool = False
    supports_inline_buttons: bool = False
    supports_modals: bool = False
    supports_reactions: bool = False
    supports_ephemeral_responses: bool = False


TELEGRAM_CAPABILITIES = PlatformCapabilities(
    supports_native_sticker_packs=True,
    supports_inline_buttons=True,
    supports_modals=False,
    supports_reactions=False,
    supports_ephemeral_responses=False,
)

DISCORD_CAPABILITIES = PlatformCapabilities(
    supports_native_sticker_packs=False,
    supports_inline_buttons=True,
    supports_modals=True,
    supports_reactions=True,
    supports_ephemeral_responses=True,
)

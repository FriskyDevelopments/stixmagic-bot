from __future__ import annotations

from typing import Protocol

from core.types import (
    PackGenerationInput,
    PackGenerationResult,
    ReactionRenderInput,
    ReactionRenderResult,
)


class StixCoreContract(Protocol):
    async def generate_pack(self, payload: PackGenerationInput) -> PackGenerationResult | None:
        """Convert incoming media into a Telegram/Discord-ready sticker payload."""

    def generate_reactions(self, payload: ReactionRenderInput) -> ReactionRenderResult:
        """Render a normalized reaction + metadata text block for platform adapters."""

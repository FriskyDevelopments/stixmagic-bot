from __future__ import annotations

from core.contracts import StixCoreContract
from core.types import PackGenerationInput, ReactionRenderInput


class DiscordStixAdapter:
    """Discord-ready scaffold using the same core contract as Telegram."""

    def __init__(self, core_engine: StixCoreContract):
        self.core_engine = core_engine

    async def generate_pack(self, file_bytes, media_type: str):
        return await self.core_engine.generate_pack(
            PackGenerationInput(file_bytes=file_bytes, media_type=media_type)
        )

    async def generate_reactions(self, *, title: str, name: str, description: str = "", likes: int = 0, dislikes: int = 0, views: int = 0, user_reaction: str | None = None) -> str:
        payload = ReactionRenderInput(
            title=title,
            name=name,
            description=description,
            likes=likes,
            dislikes=dislikes,
            views=views,
            user_reaction=user_reaction,
        )
        result = await self.core_engine.generate_reactions(payload)
        return result.text

    async def handle_slash_generate(self, interaction) -> None:
        """Placeholder command flow to mirror Telegram media->core->response lifecycle."""
        raise NotImplementedError("Wire this method to discord.py interaction handlers at deployment time.")
from __future__ import annotations

from core.contracts import StixCoreContract
from core.types import PackGenerationInput, ReactionRenderInput
from platforms.discord.wizard_renderer import DiscordWizardRenderer
from wizard.model import WizardEvent
from wizard.rendering import RenderInstruction


class DiscordStixAdapter:
    """Discord-ready scaffold using the same core and shared wizard contract as Telegram."""

    def __init__(self, core_engine: StixCoreContract) -> None:
        self.core_engine = core_engine
        self.wizard_renderer = DiscordWizardRenderer()

    async def generate_pack(self, file_bytes, media_type: str):
        return await self.core_engine.generate_pack(
            PackGenerationInput(file_bytes=file_bytes, media_type=media_type)
        )

    def generate_reactions(self, *, title: str, name: str, description: str = "", likes: int = 0, dislikes: int = 0, views: int = 0, user_reaction: str | None = None) -> str:
        payload = ReactionRenderInput(
            title=title,
            name=name,
            description=description,
            likes=likes,
            dislikes=dislikes,
            views=views,
            user_reaction=user_reaction,
        )
        return self.core_engine.generate_reactions(payload).text

    def render_wizard_event(self, event: WizardEvent) -> RenderInstruction:
        """Boundary where Discord-specific rendering starts."""
        return self.wizard_renderer.render(event)

    async def handle_slash_generate(self, interaction) -> None:
        """Placeholder command flow to mirror Telegram media->core->response lifecycle."""
        raise NotImplementedError("Wire this method to discord.py interaction handlers at deployment time.")
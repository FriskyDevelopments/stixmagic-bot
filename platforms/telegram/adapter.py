from __future__ import annotations

from dataclasses import dataclass

from core.contracts import StixCoreContract
from core.types import PackGenerationInput, ReactionRenderInput
from domain.media import extract_file_info


@dataclass(slots=True)
class TelegramMediaEnvelope:
    file_id: str
    media_type: str
    sticker_format: str


class TelegramStixAdapter:
    """Telegram transport adapter delegating business logic to the shared core engine."""

    def __init__(self, core_engine: StixCoreContract):
        self.core_engine = core_engine

    def parse_message_media(self, message) -> TelegramMediaEnvelope | None:
        file_id, media_type, sticker_format = extract_file_info(message)
        if not file_id or not media_type or not sticker_format:
            return None
        return TelegramMediaEnvelope(
            file_id=file_id,
            media_type=media_type,
            sticker_format=sticker_format,
        )

    async def generate_pack(self, file_bytes, media_type: str):
        return await self.core_engine.generate_pack(
            PackGenerationInput(file_bytes=file_bytes, media_type=media_type)
        )

    def generate_reactions(self, pack: dict, user_reaction: str | None = None) -> str:
        payload = ReactionRenderInput(
            title=pack["title"],
            name=pack["name"],
            description=pack.get("description", ""),
            likes=pack.get("likes", 0),
            dislikes=pack.get("dislikes", 0),
            views=pack.get("view_count", 0),
            user_reaction=user_reaction,
        )
        return self.core_engine.generate_reactions(payload).text

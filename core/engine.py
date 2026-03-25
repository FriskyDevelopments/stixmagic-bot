from __future__ import annotations

import html

from core.types import (
    PackGenerationInput,
    PackGenerationResult,
    ReactionRenderInput,
    ReactionRenderResult,
)
from domain.media import async_convert_to_sticker, async_convert_video_to_sticker


class StixCoreEngine:
    """Platform-agnostic STIX generation engine used by platform adapters."""

    async def generate_pack(self, payload: PackGenerationInput) -> PackGenerationResult | None:
        sticker_file = payload.file_bytes
        sticker_format = "video" if payload.media_type == "video" else "static"

        if payload.media_type == "image":
            converted = await async_convert_to_sticker(sticker_file)
            if converted:
                sticker_file = converted
        elif payload.media_type == "video":
            converted = await async_convert_video_to_sticker(sticker_file)
            if converted:
                sticker_file = converted

        return PackGenerationResult(sticker_file=sticker_file, sticker_format=sticker_format)

    def generate_reactions(self, payload: ReactionRenderInput) -> ReactionRenderResult:
        like_mark = " ◀" if payload.user_reaction == "like" else ""
        dislike_mark = " ◀" if payload.user_reaction == "dislike" else ""

        text = (
            f"🔍 <b>{html.escape(payload.title)}</b>\n"
            f"<code>{html.escape(payload.name)}</code>\n"
        )
        if payload.description:
            text += f"\n<i>{html.escape(payload.description)}</i>\n"
        text += (
            f"\n👁 {payload.views}  ·  👍 {payload.likes}{like_mark}"
            f"  ·  👎 {payload.dislikes}{dislike_mark}"
        )
        return ReactionRenderResult(text=text)

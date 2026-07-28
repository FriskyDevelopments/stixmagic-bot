from __future__ import annotations

import html

from core.types import (
    PackGenerationInput,
    PackGenerationResult,
    ReactionRenderInput,
    ReactionRenderResult,
)
from domain.media import async_convert_to_sticker, async_convert_video_to_sticker

# Minimum bytes for a valid image or video file (magic number + minimal header).
_MIN_FILE_BYTES = 8
# Telegram Bot API max file download is 20 MB.
_MAX_FILE_BYTES = 20 * 1024 * 1024


class StixCoreEngine:
    """Platform-agnostic STIX generation engine used by platform adapters."""

    async def generate_pack(self, payload: PackGenerationInput) -> PackGenerationResult | None:
        # --- Input validation for file_bytes edge cases (2.5) ---
        data = payload.file_bytes.getvalue()
        if len(data) == 0:
            # Empty file — nothing to convert.
            return None
        if len(data) < _MIN_FILE_BYTES:
            # Truncated file — too small to be a valid image/video.
            return None
        if len(data) > _MAX_FILE_BYTES:
            # Oversized file — exceeds platform upload limit.
            return None

        if payload.media_type == "image":
            converted = await async_convert_to_sticker(payload.file_bytes)
            if converted is None:
                return None
            return PackGenerationResult(sticker_file=converted, sticker_format="static")
        elif payload.media_type == "video":
            converted = await async_convert_video_to_sticker(payload.file_bytes)
            if converted is None:
                return None
            return PackGenerationResult(sticker_file=converted, sticker_format="video")
        else:
            # Unsupported media_type — return None rather than raising or
            # silently producing a static sticker.
            return None

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

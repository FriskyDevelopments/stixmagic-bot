"""Telegram adapter implementations for STIX MΛGIC shared core."""

from __future__ import annotations

import html
from dataclasses import dataclass

from core.capabilities import TELEGRAM_CAPABILITIES, PlatformCapabilities
from core.types import (
    PackGenerationResult,
    PlatformEventContext,
    ReactionRenderInput,
    ReactionRenderResult,
)
from domain.media import extract_file_info


@dataclass(slots=True)
class TelegramMediaEnvelope:
    file_id: str
    media_type: str
    sticker_format: str


class TelegramStixAdapter:
    """Legacy Telegram transport adapter retained for the existing main.py wiring."""

    def __init__(self, core_engine=None) -> None:
        # ``core_engine`` is accepted for backward compatibility but the adapter
        # now delegates directly to domain media helpers.
        self._core_engine = core_engine

    def parse_message_media(self, message) -> TelegramMediaEnvelope | None:
        file_id, media_type, sticker_format = extract_file_info(message)
        if not file_id or not media_type or not sticker_format:
            return None
        return TelegramMediaEnvelope(
            file_id=file_id,
            media_type=media_type,
            sticker_format=sticker_format,
        )

    async def generate_pack(self, file_bytes, media_type: str, sticker_format: str | None = None):
        """Generate pack by delegating to core engine.

        Args:
            file_bytes: Source file bytes or BytesIO object
            media_type: Media type from extract_file_info ("image", "video", "sticker")
            sticker_format: Optional sticker format from extract_file_info ("static", "video", "animated")
                          Used to properly detect animated stickers (e.g., Telegram video stickers)
        """
        from core.types import (
            PackGenerationRequest,
            StickerGenerationInput,
            PackItemResult,
            StickerGenerationOutput,
        )

        if self._core_engine:
            # Delegate to core engine for shared normalization logic
            # Determine if animated based on sticker_format (preferred) or fallback to media_type
            if sticker_format:
                is_animated = sticker_format in ("video", "animated")
            else:
                is_animated = media_type == "video"

            source_bytes = file_bytes.getvalue() if hasattr(file_bytes, 'getvalue') else file_bytes

            # For stickers, preserve format; for video, use video/mp4
            if media_type == "sticker":
                # Animated stickers should keep their native format, not be treated as raw video
                if sticker_format == "animated":
                    source_mime_type = "image/webp"  # Animated WebP sticker
                    prefer_format = "webp"
                elif sticker_format == "video":
                    source_mime_type = "video/webm"  # Video sticker
                    prefer_format = "webm"
                else:  # static
                    source_mime_type = "image/webp"
                    prefer_format = "webp"
            elif media_type == "video":
                source_mime_type = "video/mp4"
                prefer_format = "webm"
            else:  # image or unknown
                source_mime_type = "image/png"
                prefer_format = "webp"

            sticker_input = StickerGenerationInput(
                source_bytes=source_bytes,
                source_mime_type=source_mime_type,
                is_animated_source=is_animated,
                prefer_format=prefer_format,
            )

            request = PackGenerationRequest(
                pack_id="",
                title="",
                sticker_inputs=[sticker_input],
            )

            result = await self._core_engine.generate_pack(request, capabilities=TELEGRAM_CAPABILITIES)

            # Normalize sticker_format values: "webp" -> "static", "webm" -> "video"
            for item in result.items:
                if item.success and item.sticker:
                    raw_format = item.sticker.sticker_format
                    if raw_format == "webp":
                        item.sticker.sticker_format = "static"
                    elif raw_format == "webm":
                        item.sticker.sticker_format = "video"
                    # Note: animated webp would be handled here if needed

            return result

        # Fallback: local conversion if no core engine
        from domain.media import async_convert_to_sticker, async_convert_video_to_sticker

        sticker_file = file_bytes
        # Use sticker_format if provided, otherwise infer from media_type
        if sticker_format:
            normalized_format = sticker_format
        else:
            normalized_format = "video" if media_type == "video" else "static"

        converted = None
        if media_type == "image":
            converted = await async_convert_to_sticker(sticker_file)
            if converted:
                sticker_file = converted
        elif media_type == "video":
            converted = await async_convert_video_to_sticker(sticker_file)
            if converted:
                sticker_file = converted

        # Build new structure with PackItemResult
        # Only mark as success if conversion succeeded (or no conversion was needed)
        conversion_succeeded = (media_type in ("image", "video") and converted is not None) or media_type == "sticker"

        if conversion_succeeded:
            sticker_output = StickerGenerationOutput(
                sticker_bytes=sticker_file.getvalue() if hasattr(sticker_file, 'getvalue') else sticker_file,
                sticker_format=normalized_format
            )
            item = PackItemResult(
                index=0,
                success=True,
                sticker=sticker_output
            )
        else:
            # Conversion failed
            item = PackItemResult(
                index=0,
                success=False,
                sticker=None
            )

        return PackGenerationResult(
            pack_id="",
            title="",
            items=[item]
        )

    async def generate_reactions(self, pack: dict, user_reaction: str | None = None) -> str:
        """Generate reactions by delegating to core engine."""
        if self._core_engine:
            # Use core engine's format_pack_reactions method
            payload = ReactionRenderInput(
                title=pack['title'],
                name=pack['name'],
                description=pack.get('description', ''),
                likes=pack.get('likes', 0),
                dislikes=pack.get('dislikes', 0),
                views=pack.get('view_count', 0),
                user_reaction=user_reaction,
            )
            result = await self._core_engine.format_pack_reactions(payload)
            return result.text

        # Fallback if no core engine
        like_mark = " ◀" if user_reaction == "like" else ""
        dislike_mark = " ◀" if user_reaction == "dislike" else ""

        text = (
            f"🔍 <b>{html.escape(pack['title'])}</b>\n"
            f"<code>{html.escape(pack['name'])}</code>\n"
        )
        if pack.get("description"):
            text += f"\n<i>{html.escape(pack['description'])}</i>\n"
        text += (
            f"\n👁 {pack.get('view_count', 0)}  ·  "
            f"👍 {pack.get('likes', 0)}{like_mark}  ·  "
            f"👎 {pack.get('dislikes', 0)}{dislike_mark}"
        )
        return text


class TelegramPlatformAdapter:
    """Capability-aware Telegram adapter boundary implementing shared platform contracts."""

    @property
    def platform_name(self) -> str:
        return "telegram"

    @property
    def capabilities(self) -> PlatformCapabilities:
        return TELEGRAM_CAPABILITIES

    async def publish_pack_result(
        self,
        event: PlatformEventContext,
        result: PackGenerationResult,
    ) -> dict[str, str | int | None]:
        """Placeholder publisher hook for integration into telegram bot handlers."""

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
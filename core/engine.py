from __future__ import annotations

import io
import random
import string

from core.dtos import CoreMediaRequest, CoreMediaResult
from domain.media import (
    async_convert_to_sticker,
    async_convert_video_to_sticker,
    convert_to_sticker,
    convert_video_to_sticker,
)


class StixCoreEngine:
    """Shared STIX business logic used by transport adapters."""

    async def process_media_async(self, raw_media: io.BytesIO, request: CoreMediaRequest) -> CoreMediaResult:
        sticker_file = raw_media
        if request.media_type == "image":
            converted = await async_convert_to_sticker(raw_media)
            if converted:
                sticker_file = converted
        elif request.media_type == "video":
            converted = await async_convert_video_to_sticker(raw_media)
            if converted:
                sticker_file = converted

        return CoreMediaResult(
            sticker_file=sticker_file,
            sticker_format=request.sticker_format,
            media_type=request.media_type,
        )

    def process_media_sync(self, raw_media: io.BytesIO, request: CoreMediaRequest) -> CoreMediaResult:
        sticker_file = raw_media
        if request.media_type == "image":
            converted = convert_to_sticker(raw_media)
            if converted:
                sticker_file = converted
        elif request.media_type == "video":
            converted = convert_video_to_sticker(raw_media)
            if converted:
                sticker_file = converted

        return CoreMediaResult(
            sticker_file=sticker_file,
            sticker_format=request.sticker_format,
            media_type=request.media_type,
        )

    def generate_pack_name(self, user_id: int, bot_username: str) -> str:
        suffix = "".join(random.choices(string.ascii_lowercase, k=5))
        return f"stix_{user_id}_{suffix}_by_{bot_username}"

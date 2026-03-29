"""Backward-compatible import path for sticker media processing.

This module intentionally keeps lightweight wrappers so tests and patches
targeting `domain.media.*` continue to work even though the implementation
lives in `src.stickers.media`.
"""

from __future__ import annotations

import asyncio
import io

from src.stickers.media import (
    apply_mask_to_image as _apply_mask_to_image_impl,
    convert_to_sticker as _convert_to_sticker_impl,
    convert_video_to_sticker as _convert_video_to_sticker_impl,
    download_file_bytes as _download_file_bytes_impl,
    extract_file_info as _extract_file_info_impl,
)

__all__ = [
    "apply_mask_to_image",
    "convert_to_sticker",
    "convert_video_to_sticker",
    "download_file_bytes",
    "extract_file_info",
]

# Expose legacy API
apply_mask_to_image = _apply_mask_to_image_impl
convert_to_sticker = _convert_to_sticker_impl
convert_video_to_sticker = _convert_video_to_sticker_impl
download_file_bytes = _download_file_bytes_impl
extract_file_info = _extract_file_info_impl


async def async_convert_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, convert_to_sticker, file_bytes)


async def async_convert_video_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, convert_video_to_sticker, file_bytes)


async def async_apply_mask_to_image(
    source_bytes: io.BytesIO,
    mask_bytes: io.BytesIO,
    inverted: bool = False,
) -> io.BytesIO:
    loop = asyncio.get_event_loop()
    from functools import partial
    return await loop.run_in_executor(
        None, partial(apply_mask_to_image, source_bytes, mask_bytes, inverted=inverted)
    )

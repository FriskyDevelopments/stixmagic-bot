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
    download_file_bytes,
    extract_file_info,
)


def convert_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    return _convert_to_sticker_impl(file_bytes)


def convert_video_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    return _convert_video_to_sticker_impl(file_bytes)


def apply_mask_to_image(
    source_bytes: io.BytesIO,
    mask_bytes: io.BytesIO,
    inverted: bool = False,
) -> io.BytesIO:
    return _apply_mask_to_image_impl(source_bytes, mask_bytes, inverted=inverted)


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
    return await loop.run_in_executor(None, apply_mask_to_image, source_bytes, mask_bytes, inverted)


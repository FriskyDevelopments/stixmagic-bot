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
    "async_convert_to_sticker",
    "async_convert_video_to_sticker",
    "async_apply_mask_to_image",
]

# Expose legacy API
apply_mask_to_image = _apply_mask_to_image_impl
convert_to_sticker = _convert_to_sticker_impl
convert_video_to_sticker = _convert_video_to_sticker_impl
download_file_bytes = _download_file_bytes_impl
extract_file_info = _extract_file_info_impl


async def async_convert_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """
    Convert image bytes into a sticker image stream.
    
    Parameters:
        file_bytes (io.BytesIO): Source image data to convert into a sticker.
    
    Returns:
        io.BytesIO | None: A BytesIO containing the sticker image on success, or None if conversion failed.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, convert_to_sticker, file_bytes)


async def async_convert_video_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """
    Convert video file bytes into a sticker image stream.
    
    Parameters:
        file_bytes (io.BytesIO): Video file data to convert.
    
    Returns:
        io.BytesIO | None: `io.BytesIO` containing sticker data if conversion succeeded, `None` otherwise.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, convert_video_to_sticker, file_bytes)


async def async_apply_mask_to_image(
    source_bytes: io.BytesIO,
    mask_bytes: io.BytesIO,
    inverted: bool = False,
) -> io.BytesIO:
    """
    Apply a mask to an image and return the resulting image bytes.
    
    Parameters:
        source_bytes (io.BytesIO): Image data to which the mask will be applied.
        mask_bytes (io.BytesIO): Mask image data; nonzero/mask areas determine which pixels from the source are kept.
        inverted (bool): If True, invert the mask semantics so masked and unmasked areas are swapped.
    
    Returns:
        io.BytesIO: Bytes of the masked image.
    """
    loop = asyncio.get_running_loop()
    from functools import partial
    return await loop.run_in_executor(
        None, partial(apply_mask_to_image, source_bytes, mask_bytes, inverted=inverted)
    )
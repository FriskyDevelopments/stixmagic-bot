"""
Tests for StixCoreEngine.generate_pack — image and video paths.

Requirements covered:
  2.1 — generate_pack produces the documented PackGenerationResult for an image
        input and for a video input, with the right sticker_format in each case.
"""

from __future__ import annotations

import io

import pytest

from core.engine import StixCoreEngine
from core.types import PackGenerationInput, PackGenerationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # Fake image payload
_FAKE_VIDEO_BYTES = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 64  # Fake video payload

_FAKE_WEBP_RESULT = b"RIFF\x00\x00\x00\x00WEBP"
_FAKE_WEBM_RESULT = b"\x1a\x45\xdf\xa3"


async def _fake_async_convert_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Simulate successful image conversion."""
    return io.BytesIO(_FAKE_WEBP_RESULT)


async def _fake_async_convert_video_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Simulate successful video conversion."""
    return io.BytesIO(_FAKE_WEBM_RESULT)


# ---------------------------------------------------------------------------
# 2.1 — Image input produces static sticker_format
# ---------------------------------------------------------------------------


class TestGeneratePackImage:
    """generate_pack with media_type='image' returns a static PackGenerationResult."""

    @pytest.mark.asyncio
    async def test_returns_pack_generation_result(self, monkeypatch):
        """generate_pack returns a PackGenerationResult (not None) for image input."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _fake_async_convert_to_sticker
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="image",
        )
        result = await engine.generate_pack(payload)

        assert result is not None
        assert isinstance(result, PackGenerationResult)

    @pytest.mark.asyncio
    async def test_sticker_format_is_static(self, monkeypatch):
        """Image input produces sticker_format='static'."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _fake_async_convert_to_sticker
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="image",
        )
        result = await engine.generate_pack(payload)

        assert result.sticker_format == "static"

    @pytest.mark.asyncio
    async def test_sticker_file_is_converted_bytes(self, monkeypatch):
        """The returned sticker_file contains the converted image data."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _fake_async_convert_to_sticker
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="image",
        )
        result = await engine.generate_pack(payload)

        assert result.sticker_file.getvalue() == _FAKE_WEBP_RESULT


# ---------------------------------------------------------------------------
# 2.1 — Video input produces video sticker_format
# ---------------------------------------------------------------------------


class TestGeneratePackVideo:
    """generate_pack with media_type='video' returns a video PackGenerationResult."""

    @pytest.mark.asyncio
    async def test_returns_pack_generation_result(self, monkeypatch):
        """generate_pack returns a PackGenerationResult (not None) for video input."""
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker",
            _fake_async_convert_video_to_sticker,
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_VIDEO_BYTES),
            media_type="video",
        )
        result = await engine.generate_pack(payload)

        assert result is not None
        assert isinstance(result, PackGenerationResult)

    @pytest.mark.asyncio
    async def test_sticker_format_is_video(self, monkeypatch):
        """Video input produces sticker_format='video'."""
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker",
            _fake_async_convert_video_to_sticker,
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_VIDEO_BYTES),
            media_type="video",
        )
        result = await engine.generate_pack(payload)

        assert result.sticker_format == "video"

    @pytest.mark.asyncio
    async def test_sticker_file_is_converted_bytes(self, monkeypatch):
        """The returned sticker_file contains the converted video data."""
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker",
            _fake_async_convert_video_to_sticker,
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_VIDEO_BYTES),
            media_type="video",
        )
        result = await engine.generate_pack(payload)

        assert result.sticker_file.getvalue() == _FAKE_WEBM_RESULT

"""
Tests for StixCoreEngine.generate_pack failure paths.

Requirements covered:
  2.2 — An unsupported media_type returns the documented failure (None) rather
        than raising or silently producing a static sticker.
  2.3 — A conversion failure in domain/media.py surfaces as a result the caller
        can act on (None) — not as an unhandled exception and not as a success.
"""

from __future__ import annotations

import io

import pytest

from core.engine import StixCoreEngine
from core.types import PackGenerationInput, PackGenerationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
_FAKE_VIDEO_BYTES = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 64


async def _convert_returns_none(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Simulate a conversion failure — the converter returns None."""
    return None


async def _convert_raises(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Simulate a conversion that raises an unexpected exception."""
    raise RuntimeError("ffmpeg exploded")


# ---------------------------------------------------------------------------
# 2.2 — Unsupported media_type returns None (the documented failure)
# ---------------------------------------------------------------------------


class TestUnsupportedMediaType:
    """An unsupported media_type must not raise and must not produce a sticker."""

    @pytest.mark.asyncio
    async def test_sticker_media_type_returns_none(self, monkeypatch):
        """'sticker' is a valid MediaType literal but is not a convertible input."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _convert_returns_none
        )
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _convert_returns_none
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="sticker",
        )
        result = await engine.generate_pack(payload)

        assert result is None

    @pytest.mark.asyncio
    async def test_unsupported_media_type_does_not_raise(self, monkeypatch):
        """The engine must not raise for an unhandled media_type."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _convert_returns_none
        )
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _convert_returns_none
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="sticker",
        )
        # Must not raise — the contract says return None
        result = await engine.generate_pack(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_unsupported_media_type_does_not_silently_produce_static(self, monkeypatch):
        """Unsupported types must NOT fall through to a PackGenerationResult with format='static'."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _convert_returns_none
        )
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _convert_returns_none
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="sticker",
        )
        result = await engine.generate_pack(payload)

        # If a result is returned, it means the engine silently produced a sticker
        assert not isinstance(result, PackGenerationResult)


# ---------------------------------------------------------------------------
# 2.3 — Image conversion failure surfaces as None, not success or exception
# ---------------------------------------------------------------------------


class TestImageConversionFailure:
    """When async_convert_to_sticker returns None, generate_pack returns None."""

    @pytest.mark.asyncio
    async def test_conversion_none_returns_none(self, monkeypatch):
        """A None from the converter means the caller gets None (actionable failure)."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _convert_returns_none
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="image",
        )
        result = await engine.generate_pack(payload)

        assert result is None

    @pytest.mark.asyncio
    async def test_conversion_none_is_not_a_success(self, monkeypatch):
        """A conversion failure must not return a PackGenerationResult (success type)."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _convert_returns_none
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="image",
        )
        result = await engine.generate_pack(payload)

        assert not isinstance(result, PackGenerationResult)

    @pytest.mark.asyncio
    async def test_conversion_exception_does_not_swallow_silently(self, monkeypatch):
        """If the converter raises, the exception propagates (not swallowed as success)."""
        monkeypatch.setattr(
            "core.engine.async_convert_to_sticker", _convert_raises
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_IMAGE_BYTES),
            media_type="image",
        )
        with pytest.raises(RuntimeError, match="ffmpeg exploded"):
            await engine.generate_pack(payload)


# ---------------------------------------------------------------------------
# 2.3 — Video conversion failure surfaces as None, not success or exception
# ---------------------------------------------------------------------------


class TestVideoConversionFailure:
    """When async_convert_video_to_sticker returns None, generate_pack returns None."""

    @pytest.mark.asyncio
    async def test_conversion_none_returns_none(self, monkeypatch):
        """A None from the video converter means the caller gets None."""
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _convert_returns_none
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_VIDEO_BYTES),
            media_type="video",
        )
        result = await engine.generate_pack(payload)

        assert result is None

    @pytest.mark.asyncio
    async def test_conversion_none_is_not_a_success(self, monkeypatch):
        """A video conversion failure must not return a PackGenerationResult."""
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _convert_returns_none
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_VIDEO_BYTES),
            media_type="video",
        )
        result = await engine.generate_pack(payload)

        assert not isinstance(result, PackGenerationResult)

    @pytest.mark.asyncio
    async def test_conversion_exception_does_not_swallow_silently(self, monkeypatch):
        """If the video converter raises, the exception propagates."""
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _convert_raises
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(_FAKE_VIDEO_BYTES),
            media_type="video",
        )
        with pytest.raises(RuntimeError, match="ffmpeg exploded"):
            await engine.generate_pack(payload)

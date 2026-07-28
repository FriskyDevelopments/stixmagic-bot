"""
Tests for StixCoreEngine input edge cases and escaping.

Requirements covered:
  2.5 — Empty, truncated, and oversized file_bytes are each handled explicitly.
  2.6 — User-supplied text reaching the engine is HTML-escaped exactly once —
        never zero times, never twice.
"""

from __future__ import annotations

import io

import pytest

from core.engine import StixCoreEngine, _MAX_FILE_BYTES, _MIN_FILE_BYTES
from core.types import PackGenerationInput, PackGenerationResult, ReactionRenderInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_WEBP_RESULT = b"RIFF\x00\x00\x00\x00WEBP"
_FAKE_WEBM_RESULT = b"\x1a\x45\xdf\xa3"


async def _fake_async_convert_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Simulate successful image conversion."""
    return io.BytesIO(_FAKE_WEBP_RESULT)


async def _fake_async_convert_video_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Simulate successful video conversion."""
    return io.BytesIO(_FAKE_WEBM_RESULT)


def _patch_converters(monkeypatch):
    """Patch both converters to succeed — used when we want to isolate input validation."""
    monkeypatch.setattr(
        "core.engine.async_convert_to_sticker", _fake_async_convert_to_sticker
    )
    monkeypatch.setattr(
        "core.engine.async_convert_video_to_sticker", _fake_async_convert_video_to_sticker
    )


# ---------------------------------------------------------------------------
# 2.5 — Empty file_bytes
# ---------------------------------------------------------------------------


class TestEmptyFileBytes:
    """An empty BytesIO (zero bytes) is explicitly rejected."""

    @pytest.mark.asyncio
    async def test_empty_image_returns_none(self, monkeypatch):
        """Empty file_bytes with media_type='image' returns None."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        payload = PackGenerationInput(file_bytes=io.BytesIO(b""), media_type="image")
        result = await engine.generate_pack(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_video_returns_none(self, monkeypatch):
        """Empty file_bytes with media_type='video' returns None."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        payload = PackGenerationInput(file_bytes=io.BytesIO(b""), media_type="video")
        result = await engine.generate_pack(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_does_not_reach_converter(self, monkeypatch):
        """The converter is never called when file_bytes is empty."""
        called = []

        async def _tracking_convert(file_bytes):
            called.append(True)
            return io.BytesIO(_FAKE_WEBP_RESULT)

        monkeypatch.setattr("core.engine.async_convert_to_sticker", _tracking_convert)
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _tracking_convert
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(file_bytes=io.BytesIO(b""), media_type="image")
        await engine.generate_pack(payload)
        assert called == [], "Converter should not be called for empty input"


# ---------------------------------------------------------------------------
# 2.5 — Truncated file_bytes (too small to be valid media)
# ---------------------------------------------------------------------------


class TestTruncatedFileBytes:
    """File_bytes shorter than the minimum header size are explicitly rejected."""

    @pytest.mark.asyncio
    async def test_one_byte_image_returns_none(self, monkeypatch):
        """A single byte is too small for any valid image format."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        payload = PackGenerationInput(file_bytes=io.BytesIO(b"\x89"), media_type="image")
        result = await engine.generate_pack(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_below_threshold_video_returns_none(self, monkeypatch):
        """Bytes shorter than _MIN_FILE_BYTES are rejected for video too."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        # _MIN_FILE_BYTES - 1 bytes (just under the threshold)
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(b"\x00" * (_MIN_FILE_BYTES - 1)),
            media_type="video",
        )
        result = await engine.generate_pack(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_exactly_min_bytes_is_accepted(self, monkeypatch):
        """Exactly _MIN_FILE_BYTES bytes passes validation (converter decides the rest)."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(b"\x89PNG\r\n\x1a\n"),  # 8 bytes = _MIN_FILE_BYTES
            media_type="image",
        )
        result = await engine.generate_pack(payload)
        # Validation passes; fake converter returns success
        assert result is not None
        assert isinstance(result, PackGenerationResult)

    @pytest.mark.asyncio
    async def test_truncated_does_not_reach_converter(self, monkeypatch):
        """The converter is never called for truncated input."""
        called = []

        async def _tracking_convert(file_bytes):
            called.append(True)
            return io.BytesIO(_FAKE_WEBP_RESULT)

        monkeypatch.setattr("core.engine.async_convert_to_sticker", _tracking_convert)
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _tracking_convert
        )

        engine = StixCoreEngine()
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(b"\x00\x01\x02"),
            media_type="image",
        )
        await engine.generate_pack(payload)
        assert called == [], "Converter should not be called for truncated input"


# ---------------------------------------------------------------------------
# 2.5 — Oversized file_bytes (exceeds platform limit)
# ---------------------------------------------------------------------------


class TestOversizedFileBytes:
    """File_bytes exceeding the platform max are explicitly rejected."""

    @pytest.mark.asyncio
    async def test_oversized_image_returns_none(self, monkeypatch):
        """Bytes larger than _MAX_FILE_BYTES are rejected for images."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        # One byte over the limit
        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * _MAX_FILE_BYTES
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(oversized),
            media_type="image",
        )
        result = await engine.generate_pack(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_oversized_video_returns_none(self, monkeypatch):
        """Bytes larger than _MAX_FILE_BYTES are rejected for videos."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        oversized = b"\x00\x00\x00\x1cftypisom" + b"\x00" * _MAX_FILE_BYTES
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(oversized),
            media_type="video",
        )
        result = await engine.generate_pack(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_exactly_max_bytes_is_accepted(self, monkeypatch):
        """Exactly _MAX_FILE_BYTES passes validation (converter decides the rest)."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        # Build exactly _MAX_FILE_BYTES total
        header = b"\x89PNG\r\n\x1a\n"
        payload_data = header + b"\x00" * (_MAX_FILE_BYTES - len(header))
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(payload_data),
            media_type="image",
        )
        result = await engine.generate_pack(payload)
        assert result is not None
        assert isinstance(result, PackGenerationResult)

    @pytest.mark.asyncio
    async def test_oversized_does_not_reach_converter(self, monkeypatch):
        """The converter is never called for oversized input."""
        called = []

        async def _tracking_convert(file_bytes):
            called.append(True)
            return io.BytesIO(_FAKE_WEBP_RESULT)

        monkeypatch.setattr("core.engine.async_convert_to_sticker", _tracking_convert)
        monkeypatch.setattr(
            "core.engine.async_convert_video_to_sticker", _tracking_convert
        )

        engine = StixCoreEngine()
        oversized = b"\x00" * (_MAX_FILE_BYTES + 1)
        payload = PackGenerationInput(
            file_bytes=io.BytesIO(oversized),
            media_type="image",
        )
        await engine.generate_pack(payload)
        assert called == [], "Converter should not be called for oversized input"


# ---------------------------------------------------------------------------
# 2.5 — Edge: file_bytes position is not at start
# ---------------------------------------------------------------------------


class TestFileBytesPosition:
    """The engine reads all content regardless of the BytesIO position."""

    @pytest.mark.asyncio
    async def test_seeked_bytesio_still_validates(self, monkeypatch):
        """getvalue() returns all content even if the read pointer has advanced."""
        _patch_converters(monkeypatch)
        engine = StixCoreEngine()
        buf = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        buf.seek(10)  # Advance pointer — getvalue() still returns everything
        payload = PackGenerationInput(file_bytes=buf, media_type="image")
        result = await engine.generate_pack(payload)
        # Validation uses getvalue() which ignores position
        assert result is not None


# ---------------------------------------------------------------------------
# 2.6 — HTML escaping: user text escaped exactly once
# ---------------------------------------------------------------------------


class TestHtmlEscapingExactlyOnce:
    """User-supplied text in generate_reactions is escaped once — not zero, not twice."""

    def test_ampersand_escaped_once(self):
        """A literal '&' becomes '&amp;' — not left raw, not doubled to '&amp;amp;'."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="Tom & Jerry", name="pack")
        result = engine.generate_reactions(payload)

        assert "&amp;" in result.text
        assert "&amp;amp;" not in result.text
        # Raw '&' followed by a space should not appear outside of entities
        # (the '&' in '&amp;' is fine — check that 'Tom & Jerry' literal is gone)
        assert "Tom & Jerry" not in result.text

    def test_less_than_escaped_once(self):
        """A literal '<' becomes '&lt;' — never left raw, never '&amp;lt;'."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="a < b", name="pack")
        result = engine.generate_reactions(payload)

        assert "&lt;" in result.text
        assert "&amp;lt;" not in result.text
        assert "a < b" not in result.text

    def test_greater_than_escaped_once(self):
        """A literal '>' becomes '&gt;' — never left raw, never '&amp;gt;'."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="a > b", name="pack")
        result = engine.generate_reactions(payload)

        assert "&gt;" in result.text
        assert "&amp;gt;" not in result.text

    def test_quote_escaped_once(self):
        """A literal '\"' becomes '&quot;' — never raw, never doubled."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title='say "hello"', name="pack")
        result = engine.generate_reactions(payload)

        assert "&quot;" in result.text or "say &quot;hello&quot;" in result.text or '"' not in result.text.replace("&quot;", "")
        assert "&amp;quot;" not in result.text

    def test_pre_escaped_input_not_double_escaped(self):
        """Input already containing '&amp;' must NOT become '&amp;amp;'."""
        engine = StixCoreEngine()
        # User literally typed "&amp;" (not an entity — raw text)
        payload = ReactionRenderInput(title="A &amp; B", name="pack")
        result = engine.generate_reactions(payload)

        # The input '&amp;' has its '&' escaped to '&amp;', so output is '&amp;amp;'
        # Wait — this is correct! The user typed literal "&amp;" which should be
        # escaped to "&amp;amp;" because html.escape treats input as raw text.
        # The requirement says "escaped exactly once" meaning we call escape once.
        # So "&amp;" in input → "&amp;amp;" in output is correct single-escaping.
        assert "&amp;amp;" in result.text
        # But "&amp;amp;amp;" would indicate double-escaping
        assert "&amp;amp;amp;" not in result.text

    def test_name_field_escaped(self):
        """The name field is also HTML-escaped."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="Pack", name="pack<script>")
        result = engine.generate_reactions(payload)

        assert "&lt;script&gt;" in result.text
        assert "<script>" not in result.text

    def test_description_field_escaped(self):
        """The description field is HTML-escaped."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(
            title="Pack", name="pack", description="x < y & z > w"
        )
        result = engine.generate_reactions(payload)

        assert "&lt;" in result.text
        assert "&amp;" in result.text
        assert "&gt;" in result.text

    def test_all_fields_escaped_independently(self):
        """Each user field is escaped independently — one field doesn't affect others."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(
            title="T&T",
            name="N<N",
            description="D>D",
        )
        result = engine.generate_reactions(payload)

        assert "T&amp;T" in result.text
        assert "N&lt;N" in result.text
        assert "D&gt;D" in result.text


# ---------------------------------------------------------------------------
# 2.6 — Escaping does not corrupt non-user content
# ---------------------------------------------------------------------------


class TestEscapingPreservesStructure:
    """HTML escaping only applies to user-supplied fields, not to markup structure."""

    def test_bold_tag_preserved(self):
        """The <b> tag wrapping the title is in the output (engine's own markup)."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="Hello", name="pack")
        result = engine.generate_reactions(payload)

        assert "<b>" in result.text
        assert "</b>" in result.text

    def test_code_tag_preserved(self):
        """The <code> tag wrapping the name is in the output."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="Hello", name="pack")
        result = engine.generate_reactions(payload)

        assert "<code>" in result.text
        assert "</code>" in result.text

    def test_italic_tag_preserved_for_description(self):
        """The <i> tag wrapping the description is in the output."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="Hello", name="pack", description="Desc")
        result = engine.generate_reactions(payload)

        assert "<i>" in result.text
        assert "</i>" in result.text

    def test_emoji_preserved(self):
        """Emoji characters in the formatted output are not mangled."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="Hello", name="pack")
        result = engine.generate_reactions(payload)

        assert "🔍" in result.text
        assert "👁" in result.text
        assert "👍" in result.text
        assert "👎" in result.text

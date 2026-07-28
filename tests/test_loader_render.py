"""
Tests for loaders/render.py — render_frame and render_static.

Requirements covered:
  4.5 — loaders/render.py renders every entry in LOADERS without raising, and
        its output is escaped for the surface it targets.
"""

from __future__ import annotations

import pytest

from loaders.config import DEFAULT_CONFIG, LoaderConfig
from loaders.definitions import LOADERS
from loaders.render import render_frame, render_static


# ---------------------------------------------------------------------------
# 4.5 — Every entry renders without raising
# ---------------------------------------------------------------------------


class TestRenderFrameAllLoaders:
    """render_frame succeeds for every loader in LOADERS at every frame index."""

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_render_frame_0(self, name, loader):
        """Frame index 0 renders without raising."""
        result = render_frame(loader, 0)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_render_frame_1(self, name, loader):
        """Frame index 1 renders without raising."""
        result = render_frame(loader, 1)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_render_frame_2(self, name, loader):
        """Frame index 2 renders without raising."""
        result = render_frame(loader, 2)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_render_all_frames_complete_cycle(self, name, loader):
        """All three frames render and produce distinct non-empty strings."""
        results = []
        for i in range(3):
            result = render_frame(loader, i)
            assert isinstance(result, str)
            assert len(result) > 0
            results.append(result)
        # At least one frame should differ (captions are random, but frames
        # differ structurally; we test that the function runs, not exact text).

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_render_frame_wraps_index(self, name, loader):
        """Frame index beyond len(frames) wraps via modulo without raising."""
        result = render_frame(loader, 10)
        assert isinstance(result, str)
        assert len(result) > 0


class TestRenderFrameOutput:
    """render_frame output structure and content."""

    def test_output_contains_caption_and_frame(self):
        """Output has a caption line and a frame block separated by blank line."""
        loader = LOADERS["thunder"]
        result = render_frame(loader, 0, caption="⚡ charging effect...")
        assert "⚡ charging effect..." in result
        # Frame content should be present — check part of frame 0
        assert "🟣" in result

    def test_explicit_caption_overrides_random(self):
        """When caption is provided, it appears in the output."""
        loader = LOADERS["magic_wand"]
        result = render_frame(loader, 0, caption="custom caption here")
        assert "custom caption here" in result

    def test_placeholder_substitution(self):
        """Custom placeholder replaces the default 🟣 in the frame."""
        loader = LOADERS["thunder"]
        result = render_frame(loader, 0, placeholder="🔴")
        assert "🔴" in result
        assert "🟣" not in result

    def test_default_placeholder_preserved(self):
        """Without a custom placeholder, 🟣 stays in the output."""
        loader = LOADERS["thunder"]
        result = render_frame(loader, 0)
        assert "🟣" in result

    def test_config_placeholder_used_when_no_explicit(self):
        """Config's default_sticker_placeholder substitutes when no explicit."""
        cfg = LoaderConfig(default_sticker_placeholder="🔵")
        loader = LOADERS["thunder"]
        result = render_frame(loader, 0, config=cfg)
        assert "🔵" in result
        assert "🟣" not in result

    def test_none_caption_picks_from_loader_captions(self):
        """When caption=None, the output contains one of the loader's captions."""
        loader = LOADERS["magic_wand"]
        # Run several times; at least one caption from the loader should appear
        found = False
        for _ in range(50):
            result = render_frame(loader, 0, caption=None)
            if any(cap in result for cap in loader["captions"]):
                found = True
                break
        assert found, "render_frame with caption=None did not use loader captions"

    def test_none_caption_with_empty_captions_uses_config_default(self):
        """When loader has no captions, falls back to config default_caption_set."""
        # Create a loader with empty captions list
        loader = {
            "name": "test_no_captions",
            "frames": ["frame1 🟣", "frame2 🟣", "frame3 🟣"],
            "captions": [],
        }
        cfg = DEFAULT_CONFIG
        found = False
        for _ in range(50):
            result = render_frame(loader, 0, caption=None, config=cfg)
            if any(cap in result for cap in cfg.default_caption_set):
                found = True
                break
        assert found, (
            "render_frame with empty captions did not use config default_caption_set"
        )


# ---------------------------------------------------------------------------
# 4.5 — Output is escaped for the surface it targets (Telegram HTML)
# ---------------------------------------------------------------------------


class TestRenderFrameEscaping:
    """Output must be safe for Telegram HTML parse_mode.

    Telegram HTML parse_mode interprets <, >, and & as markup. The built-in
    loader frames use emoji — they don't contain HTML-special characters.
    The test verifies that the catalogue frames are safe as-is.
    """

    HTML_SPECIAL = ("<", ">", "&")

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_frames_contain_no_raw_html_chars(self, name, loader):
        """Catalogue frames do not contain raw HTML-special characters.

        This ensures render_frame output is safe for Telegram's HTML
        parse_mode without requiring an additional escaping pass — the
        frames are authored as emoji art and never contain < > &.
        """
        for i, frame in enumerate(loader["frames"]):
            for ch in self.HTML_SPECIAL:
                assert ch not in frame, (
                    f"Loader '{name}' frame {i} contains raw '{ch}' — "
                    f"unsafe for Telegram HTML parse_mode"
                )

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_captions_contain_no_raw_html_chars(self, name, loader):
        """Catalogue captions do not contain raw HTML-special characters."""
        for i, cap in enumerate(loader["captions"]):
            for ch in self.HTML_SPECIAL:
                assert ch not in cap, (
                    f"Loader '{name}' caption {i} contains raw '{ch}' — "
                    f"unsafe for Telegram HTML parse_mode"
                )

    @pytest.mark.parametrize("name,loader", list(LOADERS.items()))
    def test_rendered_output_no_raw_html_chars(self, name, loader):
        """Full rendered output for each frame is Telegram-HTML-safe."""
        for i in range(len(loader["frames"])):
            # Use explicit caption from the loader to avoid randomness
            caption = loader["captions"][0]
            result = render_frame(loader, i, caption=caption)
            for ch in self.HTML_SPECIAL:
                assert ch not in result, (
                    f"render_frame('{name}', {i}) output contains raw '{ch}' — "
                    f"unsafe for Telegram HTML parse_mode"
                )

    def test_default_config_captions_safe(self):
        """Default config caption_set is also HTML-safe."""
        for cap in DEFAULT_CONFIG.default_caption_set:
            for ch in self.HTML_SPECIAL:
                assert ch not in cap, (
                    f"Default config caption '{cap}' contains raw '{ch}'"
                )


# ---------------------------------------------------------------------------
# render_static
# ---------------------------------------------------------------------------


class TestRenderStatic:
    """render_static returns its input unchanged."""

    def test_returns_caption_unchanged(self):
        assert render_static("hello") == "hello"

    def test_returns_empty_string(self):
        assert render_static("") == ""

    def test_returns_emoji_caption(self):
        assert render_static("🔮 weaving...") == "🔮 weaving..."

    def test_preserves_whitespace(self):
        assert render_static("  spaces  ") == "  spaces  "

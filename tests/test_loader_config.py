"""
Tests for loaders/config.py — LoaderConfig defaults and fallback behaviour.

Requirements covered:
  4.7 — loaders/config.py applies documented defaults when config is absent,
        and a malformed config falls back rather than crashing.
"""

from __future__ import annotations

import copy
from dataclasses import fields
from unittest.mock import AsyncMock

import pytest

from loaders.config import DEFAULT_CONFIG, LoaderConfig
from loaders.render import render_frame


# ---------------------------------------------------------------------------
# 4.7 — Documented defaults when config is absent
# ---------------------------------------------------------------------------


class TestLoaderConfigDefaults:
    """LoaderConfig() with no arguments applies all documented defaults."""

    def test_default_loaders_enabled(self):
        cfg = LoaderConfig()
        assert cfg.loaders_enabled is True

    def test_default_min_duration_for_animation_ms(self):
        cfg = LoaderConfig()
        assert cfg.min_duration_for_animation_ms == 2500

    def test_default_frame_interval_ms(self):
        cfg = LoaderConfig()
        assert cfg.frame_interval_ms == 1000

    def test_default_max_frames_per_loop(self):
        cfg = LoaderConfig()
        assert cfg.max_frames_per_loop == 3

    def test_default_fallback_to_static_on_edit_failure(self):
        cfg = LoaderConfig()
        assert cfg.fallback_to_static_on_edit_failure is True

    def test_default_sticker_placeholder(self):
        cfg = LoaderConfig()
        assert cfg.default_sticker_placeholder == "🟣"

    def test_default_caption_set_is_non_empty_list(self):
        cfg = LoaderConfig()
        assert isinstance(cfg.default_caption_set, list)
        assert len(cfg.default_caption_set) > 0

    def test_default_caption_set_contains_strings(self):
        cfg = LoaderConfig()
        for caption in cfg.default_caption_set:
            assert isinstance(caption, str)
            assert len(caption) > 0


class TestDefaultConfigSingleton:
    """DEFAULT_CONFIG is the module-level shared instance with documented defaults."""

    def test_is_loader_config_instance(self):
        assert isinstance(DEFAULT_CONFIG, LoaderConfig)

    def test_has_same_values_as_fresh_instance(self):
        """DEFAULT_CONFIG should have the same field values as LoaderConfig()."""
        fresh = LoaderConfig()
        for f in fields(LoaderConfig):
            assert getattr(DEFAULT_CONFIG, f.name) == getattr(fresh, f.name), (
                f"DEFAULT_CONFIG.{f.name} differs from LoaderConfig() default"
            )


# ---------------------------------------------------------------------------
# 4.7 — No shared mutable defaults between instances
# ---------------------------------------------------------------------------


class TestNoSharedMutableDefaults:
    """Mutable default fields are not shared between instances."""

    def test_caption_set_not_shared(self):
        """Mutating one instance's default_caption_set does not affect another."""
        cfg_a = LoaderConfig()
        cfg_b = LoaderConfig()
        cfg_a.default_caption_set.append("extra caption")
        assert "extra caption" not in cfg_b.default_caption_set

    def test_caption_set_not_shared_with_default_config(self):
        """Mutating a fresh instance does not pollute DEFAULT_CONFIG."""
        original_len = len(DEFAULT_CONFIG.default_caption_set)
        cfg = LoaderConfig()
        cfg.default_caption_set.append("mutation test")
        assert len(DEFAULT_CONFIG.default_caption_set) == original_len


# ---------------------------------------------------------------------------
# 4.7 — Config absent: controller and render fall back to DEFAULT_CONFIG
# ---------------------------------------------------------------------------


class TestFallbackToDefaultConfig:
    """When config=None is passed, the system uses DEFAULT_CONFIG rather than crashing."""

    def test_render_frame_works_with_config_none(self):
        """render_frame with config=None uses DEFAULT_CONFIG successfully."""
        loader = {
            "name": "test",
            "frames": ["frame0 🟣", "frame1 🟣", "frame2 🟣"],
            "captions": ["✨ working..."],
        }
        result = render_frame(loader, 0, caption="hello", config=None)
        assert "hello" in result
        assert "frame0" in result

    def test_render_frame_uses_default_placeholder_when_config_absent(self):
        """With config=None the default placeholder 🟣 is used (no substitution)."""
        loader = {
            "name": "test",
            "frames": ["frame0 🟣"],
            "captions": ["cap"],
        }
        result = render_frame(loader, 0, caption="cap", placeholder=None, config=None)
        assert "🟣" in result

    @pytest.mark.asyncio
    async def test_controller_accepts_config_none(self):
        """LoaderController(config=None) defaults to DEFAULT_CONFIG without raising."""
        from loaders.controller import LoaderController

        msg = AsyncMock()
        loader = {
            "name": "test",
            "frames": ["frame0 🟣"],
            "captions": ["cap"],
        }
        ctrl = LoaderController(msg, loader, config=None)
        assert ctrl._config is DEFAULT_CONFIG

    @pytest.mark.asyncio
    async def test_session_accepts_config_none(self):
        """LoaderSession(config=None) defaults without crashing."""
        from loaders.controller import LoaderSession

        msg = AsyncMock()
        loader = {
            "name": "test",
            "frames": ["frame0 🟣"],
            "captions": ["cap"],
        }
        session = LoaderSession(msg, loader, config=None)
        assert session.controller._config is DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# 4.7 — Malformed config falls back rather than crashing
# ---------------------------------------------------------------------------


class TestMalformedConfigFallback:
    """A malformed or partial config does not crash the system."""

    def test_partial_override_keeps_other_defaults(self):
        """Overriding one field leaves the rest at documented defaults."""
        cfg = LoaderConfig(frame_interval_ms=500)
        assert cfg.frame_interval_ms == 500
        # All other fields still at default
        assert cfg.loaders_enabled is True
        assert cfg.min_duration_for_animation_ms == 2500
        assert cfg.max_frames_per_loop == 3
        assert cfg.fallback_to_static_on_edit_failure is True
        assert cfg.default_sticker_placeholder == "🟣"
        assert isinstance(cfg.default_caption_set, list)
        assert len(cfg.default_caption_set) > 0

    def test_zero_frame_interval_does_not_crash_render(self):
        """frame_interval_ms=0 does not crash — used only as a sleep argument."""
        cfg = LoaderConfig(frame_interval_ms=0)
        loader = {
            "name": "test",
            "frames": ["frame 🟣"],
            "captions": ["cap"],
        }
        result = render_frame(loader, 0, caption="cap", config=cfg)
        assert isinstance(result, str)

    def test_zero_max_frames_per_loop_does_not_crash_render(self):
        """max_frames_per_loop=0 — render_frame still works (modulo uses frame count)."""
        cfg = LoaderConfig(max_frames_per_loop=0)
        loader = {
            "name": "test",
            "frames": ["frame0 🟣", "frame1 🟣"],
            "captions": ["cap"],
        }
        # render_frame directly uses frame_idx % len(frames), not max_frames_per_loop
        result = render_frame(loader, 0, caption="cap", config=cfg)
        assert isinstance(result, str)

    def test_empty_caption_set_still_allows_explicit_caption(self):
        """An empty default_caption_set works if an explicit caption is passed."""
        cfg = LoaderConfig(default_caption_set=[])
        loader = {
            "name": "test",
            "frames": ["frame 🟣"],
            "captions": [],
        }
        result = render_frame(loader, 0, caption="explicit", config=cfg)
        assert "explicit" in result

    def test_negative_min_duration_does_not_crash(self):
        """A negative min_duration_for_animation_ms is not useful but must not crash."""
        cfg = LoaderConfig(min_duration_for_animation_ms=-1)
        assert cfg.min_duration_for_animation_ms == -1
        # The controller would just skip the delay — validate it doesn't raise

    def test_custom_placeholder_substitutes_in_render(self):
        """A custom placeholder replaces the default 🟣 in frames."""
        cfg = LoaderConfig(default_sticker_placeholder="🔥")
        loader = {
            "name": "test",
            "frames": ["spark 🟣 glow"],
            "captions": ["cap"],
        }
        result = render_frame(loader, 0, caption="cap", config=cfg)
        assert "🔥" in result
        assert "🟣" not in result

    def test_render_with_loader_missing_captions_key(self):
        """A loader dict missing 'captions' falls back to config's default_caption_set."""
        cfg = LoaderConfig()
        loader = {
            "name": "no_captions",
            "frames": ["frame 🟣"],
        }
        # caption=None triggers the fallback path
        result = render_frame(loader, 0, caption=None, config=cfg)
        # Should pick from default_caption_set; result should be a string
        assert isinstance(result, str)
        assert "frame" in result

    def test_render_with_loader_empty_captions_uses_default_set(self):
        """A loader with captions=[] falls back to config's default_caption_set."""
        cfg = LoaderConfig()
        loader = {
            "name": "empty_captions",
            "frames": ["frame 🟣"],
            "captions": [],
        }
        result = render_frame(loader, 0, caption=None, config=cfg)
        assert isinstance(result, str)
        # The caption came from cfg.default_caption_set
        found_default_caption = any(
            cap in result for cap in cfg.default_caption_set
        )
        assert found_default_caption, (
            f"Expected one of default captions in result, got: {result}"
        )

    @pytest.mark.asyncio
    async def test_controller_with_loader_missing_captions_falls_back(self):
        """LoaderController with a loader missing 'captions' picks from config defaults."""
        from loaders.controller import LoaderController

        msg = AsyncMock()
        loader = {
            "name": "sparse",
            "frames": ["frame 🟣"],
        }
        # Should not raise
        ctrl = LoaderController(msg, loader, config=LoaderConfig())
        # Caption should have been picked from the config default set
        assert ctrl._caption in LoaderConfig().default_caption_set


# ---------------------------------------------------------------------------
# 4.7 — Type coercion edge cases (dataclass doesn't validate types)
# ---------------------------------------------------------------------------


class TestConfigTypeEdgeCases:
    """Python dataclasses don't enforce types — verify the system is robust."""

    def test_non_bool_loaders_enabled_truthy(self):
        """A truthy non-bool loaders_enabled doesn't crash the boolean check."""
        cfg = LoaderConfig(loaders_enabled=1)  # type: ignore[arg-type]
        # The controller checks `if not self._config.loaders_enabled`
        # 1 is truthy, so it should behave as enabled
        assert cfg.loaders_enabled

    def test_non_bool_loaders_enabled_falsy(self):
        """A falsy non-bool loaders_enabled disables loaders without crashing."""
        cfg = LoaderConfig(loaders_enabled=0)  # type: ignore[arg-type]
        assert not cfg.loaders_enabled

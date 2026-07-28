"""
Tests for core/contracts.py and core/types.py — input/output dataclasses.

Requirements covered:
  3.1 — Every input dataclass rejects a missing required field rather than
        producing a half-built object.
  3.2 — Optional fields have the documented defaults, and a default is never
        a shared mutable.
"""

from __future__ import annotations

import io

import pytest

from core.types import (
    PackGenerationInput,
    PackGenerationResult,
    ReactionRenderInput,
    ReactionRenderResult,
)


# ---------------------------------------------------------------------------
# 3.1 — Required fields must not be omissible
# ---------------------------------------------------------------------------


class TestPackGenerationInputRequired:
    """PackGenerationInput requires file_bytes and media_type."""

    def test_rejects_no_args(self):
        with pytest.raises(TypeError):
            PackGenerationInput()  # type: ignore[call-arg]

    def test_rejects_missing_file_bytes(self):
        with pytest.raises(TypeError):
            PackGenerationInput(media_type="image")  # type: ignore[call-arg]

    def test_rejects_missing_media_type(self):
        with pytest.raises(TypeError):
            PackGenerationInput(file_bytes=io.BytesIO(b"x"))  # type: ignore[call-arg]

    def test_accepts_both_required(self):
        buf = io.BytesIO(b"png data")
        obj = PackGenerationInput(file_bytes=buf, media_type="image")
        assert obj.file_bytes is buf
        assert obj.media_type == "image"


class TestPackGenerationResultRequired:
    """PackGenerationResult requires sticker_file and sticker_format."""

    def test_rejects_no_args(self):
        with pytest.raises(TypeError):
            PackGenerationResult()  # type: ignore[call-arg]

    def test_rejects_missing_sticker_file(self):
        with pytest.raises(TypeError):
            PackGenerationResult(sticker_format="static")  # type: ignore[call-arg]

    def test_rejects_missing_sticker_format(self):
        with pytest.raises(TypeError):
            PackGenerationResult(sticker_file=io.BytesIO(b"x"))  # type: ignore[call-arg]

    def test_accepts_both_required(self):
        buf = io.BytesIO(b"webp data")
        obj = PackGenerationResult(sticker_file=buf, sticker_format="static")
        assert obj.sticker_file is buf
        assert obj.sticker_format == "static"


class TestReactionRenderInputRequired:
    """ReactionRenderInput requires title and name; the rest are optional."""

    def test_rejects_no_args(self):
        with pytest.raises(TypeError):
            ReactionRenderInput()  # type: ignore[call-arg]

    def test_rejects_missing_title(self):
        with pytest.raises(TypeError):
            ReactionRenderInput(name="pack1")  # type: ignore[call-arg]

    def test_rejects_missing_name(self):
        with pytest.raises(TypeError):
            ReactionRenderInput(title="My Pack")  # type: ignore[call-arg]

    def test_accepts_required_only(self):
        obj = ReactionRenderInput(title="Pack", name="pack1")
        assert obj.title == "Pack"
        assert obj.name == "pack1"


class TestReactionRenderResultRequired:
    """ReactionRenderResult requires text."""

    def test_rejects_no_args(self):
        with pytest.raises(TypeError):
            ReactionRenderResult()  # type: ignore[call-arg]

    def test_accepts_text(self):
        obj = ReactionRenderResult(text="hello")
        assert obj.text == "hello"


# ---------------------------------------------------------------------------
# 3.2 — Optional defaults are correct and never shared mutable
# ---------------------------------------------------------------------------


class TestReactionRenderInputDefaults:
    """Optional fields on ReactionRenderInput have the documented defaults."""

    def test_description_defaults_to_empty_string(self):
        obj = ReactionRenderInput(title="T", name="n")
        assert obj.description == ""

    def test_likes_defaults_to_zero(self):
        obj = ReactionRenderInput(title="T", name="n")
        assert obj.likes == 0

    def test_dislikes_defaults_to_zero(self):
        obj = ReactionRenderInput(title="T", name="n")
        assert obj.dislikes == 0

    def test_views_defaults_to_zero(self):
        obj = ReactionRenderInput(title="T", name="n")
        assert obj.views == 0

    def test_user_reaction_defaults_to_none(self):
        obj = ReactionRenderInput(title="T", name="n")
        assert obj.user_reaction is None

    def test_defaults_are_not_shared_mutable(self):
        """
        Ensure that default values are immutable (str, int, None) and not
        shared mutable containers. Two instances must not share default state.
        """
        a = ReactionRenderInput(title="T", name="n")
        b = ReactionRenderInput(title="T", name="n")

        # Scalar defaults are equal but do not alias anything dangerous.
        # The key invariant: mutating one instance's field can never affect
        # the other. With slots=True and immutable defaults this holds, but
        # we verify explicitly.
        assert a.description == b.description
        assert a.likes == b.likes
        assert a.dislikes == b.dislikes
        assert a.views == b.views
        assert a.user_reaction == b.user_reaction

        # If description were a list default, this would expose aliasing:
        # (It's a str, so this is a sanity belt.)
        assert type(a.description) is str  # not a mutable container
        assert type(a.likes) is int
        assert type(a.dislikes) is int
        assert type(a.views) is int


class TestPackGenerationInputNoHiddenDefaults:
    """PackGenerationInput has no optional fields — all are required."""

    def test_no_default_for_file_bytes(self):
        """file_bytes has no default; cannot be constructed without it."""
        with pytest.raises(TypeError):
            PackGenerationInput(media_type="image")  # type: ignore[call-arg]

    def test_no_default_for_media_type(self):
        """media_type has no default; cannot be constructed without it."""
        with pytest.raises(TypeError):
            PackGenerationInput(file_bytes=io.BytesIO(b"x"))  # type: ignore[call-arg]


class TestPackGenerationResultNoHiddenDefaults:
    """PackGenerationResult has no optional fields — all are required."""

    def test_no_default_for_sticker_file(self):
        with pytest.raises(TypeError):
            PackGenerationResult(sticker_format="video")  # type: ignore[call-arg]

    def test_no_default_for_sticker_format(self):
        with pytest.raises(TypeError):
            PackGenerationResult(sticker_file=io.BytesIO(b"x"))  # type: ignore[call-arg]

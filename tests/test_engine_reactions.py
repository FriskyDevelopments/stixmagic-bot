"""
Tests for StixCoreEngine.generate_reactions — reaction rendering.

Requirements covered:
  2.4 — render_reaction / ReactionRenderResult follows the same contract as
        pack generation, including its failure path.
"""

from __future__ import annotations

import pytest

from core.engine import StixCoreEngine
from core.types import ReactionRenderInput, ReactionRenderResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_input(**kwargs) -> ReactionRenderInput:
    """Build a ReactionRenderInput with sensible defaults."""
    defaults = {
        "title": "Cool Pack",
        "name": "cool_pack_by_stixmagicbot",
        "description": "",
        "likes": 0,
        "dislikes": 0,
        "views": 0,
        "user_reaction": None,
    }
    defaults.update(kwargs)
    return ReactionRenderInput(**defaults)


# ---------------------------------------------------------------------------
# 2.4 — generate_reactions returns a ReactionRenderResult
# ---------------------------------------------------------------------------


class TestReactionRenderResult:
    """generate_reactions returns a well-formed ReactionRenderResult."""

    def test_returns_reaction_render_result(self):
        """The return type is always ReactionRenderResult."""
        engine = StixCoreEngine()
        payload = _make_input()
        result = engine.generate_reactions(payload)

        assert isinstance(result, ReactionRenderResult)

    def test_result_has_text_field(self):
        """The result has a non-empty text field."""
        engine = StixCoreEngine()
        payload = _make_input(title="Test Pack", name="test_pack")
        result = engine.generate_reactions(payload)

        assert hasattr(result, "text")
        assert isinstance(result.text, str)
        assert len(result.text) > 0

    def test_title_appears_in_output(self):
        """The title from the input is rendered into the output text."""
        engine = StixCoreEngine()
        payload = _make_input(title="My Stickers")
        result = engine.generate_reactions(payload)

        assert "My Stickers" in result.text

    def test_name_appears_in_output(self):
        """The pack name from the input is rendered into the output text."""
        engine = StixCoreEngine()
        payload = _make_input(name="my_pack_by_stixmagicbot")
        result = engine.generate_reactions(payload)

        assert "my_pack_by_stixmagicbot" in result.text

    def test_description_appears_when_provided(self):
        """When description is non-empty, it appears in the output."""
        engine = StixCoreEngine()
        payload = _make_input(description="A lovely sticker set")
        result = engine.generate_reactions(payload)

        assert "A lovely sticker set" in result.text

    def test_description_absent_when_empty(self):
        """When description is empty, no extra blank description section appears."""
        engine = StixCoreEngine()
        payload = _make_input(description="")
        result = engine.generate_reactions(payload)

        # The text should not contain an italic-wrapped empty string
        assert "<i></i>" not in result.text


# ---------------------------------------------------------------------------
# 2.4 — Counters and reaction marks
# ---------------------------------------------------------------------------


class TestReactionCounters:
    """Counters (likes, dislikes, views) and reaction indicators render correctly."""

    def test_counters_appear_in_output(self):
        """Likes, dislikes, and views are rendered as numbers in the text."""
        engine = StixCoreEngine()
        payload = _make_input(likes=42, dislikes=7, views=100)
        result = engine.generate_reactions(payload)

        assert "42" in result.text
        assert "7" in result.text
        assert "100" in result.text

    def test_like_reaction_shows_mark(self):
        """When user_reaction is 'like', a mark appears next to the like count."""
        engine = StixCoreEngine()
        payload = _make_input(likes=5, user_reaction="like")
        result = engine.generate_reactions(payload)

        # The like mark (◀) should appear after the likes count
        assert "◀" in result.text

    def test_dislike_reaction_shows_mark(self):
        """When user_reaction is 'dislike', a mark appears next to the dislike count."""
        engine = StixCoreEngine()
        payload = _make_input(dislikes=3, user_reaction="dislike")
        result = engine.generate_reactions(payload)

        assert "◀" in result.text

    def test_no_reaction_no_mark(self):
        """When user_reaction is None, no indicator mark appears."""
        engine = StixCoreEngine()
        payload = _make_input(user_reaction=None)
        result = engine.generate_reactions(payload)

        assert "◀" not in result.text

    def test_like_mark_not_on_dislike_side(self):
        """When user_reaction is 'like', the mark is on the like side, not dislike."""
        engine = StixCoreEngine()
        payload = _make_input(likes=10, dislikes=2, user_reaction="like")
        result = engine.generate_reactions(payload)

        # The text has format: 👍 {likes}{like_mark}  ·  👎 {dislikes}{dislike_mark}
        # With user_reaction="like", like_mark=" ◀" and dislike_mark=""
        like_section = result.text.split("👍")[1].split("👎")[0]
        dislike_section = result.text.split("👎")[1]

        assert "◀" in like_section
        assert "◀" not in dislike_section

    def test_dislike_mark_not_on_like_side(self):
        """When user_reaction is 'dislike', the mark is on the dislike side, not like."""
        engine = StixCoreEngine()
        payload = _make_input(likes=10, dislikes=2, user_reaction="dislike")
        result = engine.generate_reactions(payload)

        like_section = result.text.split("👍")[1].split("👎")[0]
        dislike_section = result.text.split("👎")[1]

        assert "◀" not in like_section
        assert "◀" in dislike_section


# ---------------------------------------------------------------------------
# 2.4 — HTML escaping in reaction output
# ---------------------------------------------------------------------------


class TestReactionEscaping:
    """User-supplied text in reaction renders is HTML-escaped for Telegram."""

    def test_title_is_html_escaped(self):
        """HTML special characters in title are escaped."""
        engine = StixCoreEngine()
        payload = _make_input(title="Pack <script>&evil")
        result = engine.generate_reactions(payload)

        assert "&lt;script&gt;" in result.text
        assert "&amp;evil" in result.text
        # The raw unescaped form must not appear
        assert "<script>" not in result.text

    def test_name_is_html_escaped(self):
        """HTML special characters in name are escaped."""
        engine = StixCoreEngine()
        payload = _make_input(name="pack<>&name")
        result = engine.generate_reactions(payload)

        assert "&lt;" in result.text
        assert "&gt;" in result.text
        assert "&amp;" in result.text

    def test_description_is_html_escaped(self):
        """HTML special characters in description are escaped."""
        engine = StixCoreEngine()
        payload = _make_input(description='<img src="x">')
        result = engine.generate_reactions(payload)

        assert "&lt;img" in result.text
        assert "<img" not in result.text

    def test_escaping_not_doubled(self):
        """A pre-escaped ampersand must not become &amp;amp;."""
        engine = StixCoreEngine()
        # Input has a literal ampersand — it should be escaped once to &amp;
        payload = _make_input(title="Tom & Jerry")
        result = engine.generate_reactions(payload)

        assert "Tom &amp; Jerry" in result.text
        assert "Tom &amp;amp; Jerry" not in result.text


# ---------------------------------------------------------------------------
# 2.4 — Contract: generate_reactions never returns None
# ---------------------------------------------------------------------------


class TestReactionContract:
    """generate_reactions follows the same contract philosophy as generate_pack."""

    def test_never_returns_none(self):
        """Unlike generate_pack (which returns None on failure), generate_reactions
        always returns a ReactionRenderResult since it does pure text formatting
        with no fallible I/O."""
        engine = StixCoreEngine()
        payload = _make_input()
        result = engine.generate_reactions(payload)

        assert result is not None

    def test_zero_counters_still_render(self):
        """All counters at zero still produces a valid result."""
        engine = StixCoreEngine()
        payload = _make_input(likes=0, dislikes=0, views=0)
        result = engine.generate_reactions(payload)

        assert isinstance(result, ReactionRenderResult)
        assert "0" in result.text

    def test_minimal_input_renders(self):
        """Only required fields (title, name) with all defaults produces output."""
        engine = StixCoreEngine()
        payload = ReactionRenderInput(title="X", name="y")
        result = engine.generate_reactions(payload)

        assert isinstance(result, ReactionRenderResult)
        assert "X" in result.text
        assert "y" in result.text

    def test_large_counters_render(self):
        """Very large counter values do not break rendering."""
        engine = StixCoreEngine()
        payload = _make_input(likes=999999, dislikes=888888, views=1000000)
        result = engine.generate_reactions(payload)

        assert "999999" in result.text
        assert "888888" in result.text
        assert "1000000" in result.text

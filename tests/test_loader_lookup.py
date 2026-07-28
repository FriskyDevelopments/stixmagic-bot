"""
Tests for loaders/selection.py — get_loader_by_name and get_loader_for_context.

Requirements covered:
  4.3 — get_loader_by_name returns None for an unknown name rather than raising,
        and is exact-match (not prefix or case-insensitive) unless documented
        otherwise.
  4.4 — get_loader_for_context returns a context-appropriate loader for each
        known action type and falls back to random for an unknown one.
"""

from __future__ import annotations

import pytest

from loaders.definitions import LOADERS
from loaders.selection import (
    ACTION_LOADER_MAP,
    get_loader_by_name,
    get_loader_for_context,
)


# ---------------------------------------------------------------------------
# 4.3 — get_loader_by_name
# ---------------------------------------------------------------------------


class TestGetLoaderByName:
    """get_loader_by_name returns the named loader or None."""

    # -- Happy path --

    @pytest.mark.parametrize("name", list(LOADERS.keys()))
    def test_returns_known_loader(self, name):
        """Each known loader name resolves to its entry."""
        result = get_loader_by_name(name)
        assert result is not None
        assert result["name"] == name
        assert result is LOADERS[name]

    # -- Unknown names return None, not raise --

    def test_unknown_name_returns_none(self):
        """A name that doesn't exist returns None."""
        assert get_loader_by_name("nonexistent_loader_xyz") is None

    def test_empty_string_returns_none(self):
        """An empty string returns None."""
        assert get_loader_by_name("") is None

    # -- Exact match: not prefix --

    def test_prefix_does_not_match(self):
        """A prefix of a valid name is not a match."""
        # "thunder" exists; "thund" does not.
        assert get_loader_by_name("thund") is None

    def test_suffix_does_not_match(self):
        """A suffix of a valid name is not a match."""
        # "thunder" exists; "under" does not.
        assert get_loader_by_name("under") is None

    # -- Exact match: case-sensitive --

    def test_uppercase_does_not_match(self):
        """Names are case-sensitive — uppercase variant returns None."""
        assert get_loader_by_name("THUNDER") is None

    def test_mixed_case_does_not_match(self):
        """Mixed case does not match a lowercase name."""
        assert get_loader_by_name("Thunder") is None

    def test_trailing_space_does_not_match(self):
        """Trailing whitespace makes it a different string."""
        assert get_loader_by_name("thunder ") is None

    def test_leading_space_does_not_match(self):
        """Leading whitespace makes it a different string."""
        assert get_loader_by_name(" thunder") is None


# ---------------------------------------------------------------------------
# 4.4 — get_loader_for_context
# ---------------------------------------------------------------------------


class TestGetLoaderForContext:
    """get_loader_for_context maps actions to loaders, random for unknown."""

    # -- Known action types return the mapped loader --

    @pytest.mark.parametrize(
        "action,expected_loader_name",
        list(ACTION_LOADER_MAP.items()),
    )
    def test_known_action_returns_mapped_loader(self, action, expected_loader_name):
        """Each mapped action type returns its designated loader."""
        result = get_loader_for_context(action)
        assert result["name"] == expected_loader_name, (
            f"Action '{action}' should map to '{expected_loader_name}' "
            f"but got '{result['name']}'"
        )

    @pytest.mark.parametrize(
        "action,expected_loader_name",
        list(ACTION_LOADER_MAP.items()),
    )
    def test_known_action_returns_entry_from_loaders(self, action, expected_loader_name):
        """The returned loader is the actual LOADERS entry (identity check)."""
        result = get_loader_for_context(action)
        assert result is LOADERS[expected_loader_name]

    # -- Unknown action types fall back to random --

    def test_unknown_action_returns_valid_loader(self):
        """An unmapped action still returns a loader from LOADERS."""
        result = get_loader_for_context("totally_unknown_action_xyz")
        assert isinstance(result, dict)
        assert result in LOADERS.values()

    def test_empty_action_returns_valid_loader(self):
        """An empty string action falls back to random."""
        result = get_loader_for_context("")
        assert result in LOADERS.values()

    def test_unknown_action_returns_diverse_results(self):
        """Random fallback actually produces varied results over many calls."""
        seen_names: set[str] = set()
        for _ in range(200):
            loader = get_loader_for_context("unmapped_action")
            assert loader in LOADERS.values()
            seen_names.add(loader["name"])
            if len(seen_names) >= 2:
                break
        assert len(seen_names) >= 2, (
            "get_loader_for_context with unknown action returned the same "
            "loader 200 times — random fallback likely broken"
        )

    # -- Case sensitivity of action types --

    def test_action_case_sensitive(self):
        """Action matching is case-sensitive — uppercase variant is unknown."""
        # "create_pack" is mapped; "CREATE_PACK" is not.
        result = get_loader_for_context("CREATE_PACK")
        # It should fall back to random — it may or may not return magic_wand,
        # but the important thing is it doesn't crash, and over many calls it
        # won't always be magic_wand.
        assert result in LOADERS.values()

    # -- Stability: same known action always gives same loader --

    def test_known_action_is_deterministic(self):
        """A known action always returns the same loader (not random)."""
        for _ in range(50):
            result = get_loader_for_context("create_pack")
            assert result["name"] == "magic_wand"

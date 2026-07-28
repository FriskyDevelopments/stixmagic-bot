"""
Tests for loaders/definitions.py catalogue and loaders/selection.get_random_loader.

Requirements covered:
  4.1 — LOADERS is well-formed: every entry has the keys the renderer reads,
        and no two entries share a name.
  4.2 — get_random_loader only ever returns an entry from LOADERS.
"""

from __future__ import annotations

import pytest

from loaders.definitions import LOADERS
from loaders.selection import get_random_loader


# ---------------------------------------------------------------------------
# 4.1 — Catalogue well-formedness
# ---------------------------------------------------------------------------


class TestLoaderCatalogueStructure:
    """Every entry in LOADERS has the keys the renderer reads."""

    def test_catalogue_is_non_empty(self):
        assert len(LOADERS) > 0, "LOADERS must contain at least one entry"

    @pytest.mark.parametrize("key,loader", list(LOADERS.items()))
    def test_has_name_key(self, key, loader):
        """Each loader dict has a 'name' string."""
        assert "name" in loader, f"Loader '{key}' missing 'name' key"
        assert isinstance(loader["name"], str)

    @pytest.mark.parametrize("key,loader", list(LOADERS.items()))
    def test_name_matches_dict_key(self, key, loader):
        """The 'name' value matches the dictionary key."""
        assert loader["name"] == key, (
            f"Loader key '{key}' does not match its name field '{loader['name']}'"
        )

    @pytest.mark.parametrize("key,loader", list(LOADERS.items()))
    def test_has_frames_key(self, key, loader):
        """Each loader dict has a 'frames' list."""
        assert "frames" in loader, f"Loader '{key}' missing 'frames' key"
        assert isinstance(loader["frames"], list)

    @pytest.mark.parametrize("key,loader", list(LOADERS.items()))
    def test_frames_has_exactly_three(self, key, loader):
        """The documentation specifies exactly 3 frames per loader."""
        assert len(loader["frames"]) == 3, (
            f"Loader '{key}' has {len(loader['frames'])} frames, expected 3"
        )

    @pytest.mark.parametrize("key,loader", list(LOADERS.items()))
    def test_frames_are_non_empty_strings(self, key, loader):
        """Each frame is a non-empty string."""
        for i, frame in enumerate(loader["frames"]):
            assert isinstance(frame, str), (
                f"Loader '{key}' frame {i} is not a string"
            )
            assert len(frame) > 0, (
                f"Loader '{key}' frame {i} is empty"
            )

    @pytest.mark.parametrize("key,loader", list(LOADERS.items()))
    def test_has_captions_key(self, key, loader):
        """Each loader dict has a 'captions' list."""
        assert "captions" in loader, f"Loader '{key}' missing 'captions' key"
        assert isinstance(loader["captions"], list)

    @pytest.mark.parametrize("key,loader", list(LOADERS.items()))
    def test_captions_non_empty(self, key, loader):
        """Each loader has at least one caption string."""
        assert len(loader["captions"]) >= 1, (
            f"Loader '{key}' has no captions"
        )
        for i, cap in enumerate(loader["captions"]):
            assert isinstance(cap, str), (
                f"Loader '{key}' caption {i} is not a string"
            )
            assert len(cap) > 0, (
                f"Loader '{key}' caption {i} is empty"
            )

    def test_no_duplicate_names(self):
        """No two entries share a name value."""
        names = [loader["name"] for loader in LOADERS.values()]
        assert len(names) == len(set(names)), (
            f"Duplicate loader names found: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_dict_keys_are_unique(self):
        """Dictionary keys are unique by definition, but verify name↔key."""
        # Redundant with test_name_matches_dict_key across all entries,
        # but this gives a single assertion over the full set.
        keys = list(LOADERS.keys())
        names = [LOADERS[k]["name"] for k in keys]
        assert keys == names


# ---------------------------------------------------------------------------
# 4.2 — get_random_loader only returns entries from LOADERS
# ---------------------------------------------------------------------------


class TestGetRandomLoader:
    """get_random_loader returns only entries that exist in LOADERS."""

    def test_returns_a_dict(self):
        loader = get_random_loader()
        assert isinstance(loader, dict)

    def test_returns_entry_from_loaders(self):
        """A single call returns one of the known LOADERS values."""
        loader = get_random_loader()
        assert loader in LOADERS.values(), (
            f"get_random_loader returned unknown loader: {loader.get('name')}"
        )

    def test_repeated_calls_always_from_loaders(self):
        """Run many iterations to increase confidence in randomness coverage."""
        loaders_values = list(LOADERS.values())
        for _ in range(200):
            loader = get_random_loader()
            assert loader in loaders_values, (
                f"get_random_loader returned unknown loader: {loader.get('name')}"
            )

    def test_random_returns_diverse_results(self):
        """Over many calls, at least 2 distinct loaders are returned."""
        seen_names = set()
        for _ in range(100):
            loader = get_random_loader()
            seen_names.add(loader["name"])
            if len(seen_names) >= 2:
                break
        assert len(seen_names) >= 2, (
            "get_random_loader returned the same loader 100 times in a row — "
            "likely broken randomness"
        )

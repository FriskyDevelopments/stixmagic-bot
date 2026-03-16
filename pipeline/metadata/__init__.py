"""
pipeline/metadata/__init__.py – MagicStix asset catalog persistence.

The catalog is stored as a JSON file on disk (``assets/catalog.json`` by
default) and provides simple CRUD-style helpers for the pipeline.

Usage
-----
>>> from pipeline.metadata import AssetCatalog
>>> catalog = AssetCatalog()
>>> catalog.load()
>>> asset = catalog.get("letter_A")
>>> catalog.add(asset)
>>> catalog.save()
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pipeline.asset_model import Asset, AssetCategory, AssetTheme

logger = logging.getLogger(__name__)

DEFAULT_CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets", "catalog.json"
)


class AssetCatalog:
    """
    In-memory asset registry backed by a JSON file.

    The catalog is lazily loaded; call :meth:`load` explicitly or pass
    ``auto_load=True`` to ``__init__``.
    """

    def __init__(self, path: str = DEFAULT_CATALOG_PATH, *, auto_load: bool = False) -> None:
        self._path = os.path.abspath(path)
        self._assets: dict[str, Asset] = {}
        if auto_load and os.path.exists(self._path):
            self.load()

    # ── Persistence ───────────────────────────────────────────

    def load(self) -> None:
        """Load / reload the catalog from disk.  Missing file is treated as empty."""
        if not os.path.exists(self._path):
            logger.info("Catalog not found at %s — starting empty.", self._path)
            return
        try:
            with open(self._path, encoding="utf-8") as fh:
                raw: list[dict[str, Any]] = json.load(fh)
            self._assets = {item["id"]: Asset.from_dict(item) for item in raw}
            logger.info("Loaded %d assets from catalog.", len(self._assets))
        except Exception as exc:
            logger.error("Failed to load catalog: %s", exc)

    def save(self) -> None:
        """Persist the current in-memory catalog to disk."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump([a.to_dict() for a in self._assets.values()], fh, indent=2)
            logger.info("Saved %d assets to catalog.", len(self._assets))
        except Exception as exc:
            logger.error("Failed to save catalog: %s", exc)

    # ── CRUD ──────────────────────────────────────────────────

    def add(self, asset: Asset) -> None:
        """Insert or overwrite an asset record."""
        self._assets[asset.id] = asset

    def remove(self, asset_id: str) -> bool:
        """Remove an asset by id.  Returns True if it existed."""
        return self._assets.pop(asset_id, None) is not None

    def get(self, asset_id: str) -> Asset | None:
        """Return the asset with the given id, or None."""
        return self._assets.get(asset_id)

    def all(self) -> list[Asset]:
        """Return all assets as a list."""
        return list(self._assets.values())

    # ── Querying ──────────────────────────────────────────────

    def by_category(self, category: AssetCategory) -> list[Asset]:
        """Return assets matching the given category."""
        return [a for a in self._assets.values() if a.category == category]

    def by_theme(self, theme: AssetTheme) -> list[Asset]:
        """Return assets matching the given theme."""
        return [a for a in self._assets.values() if a.theme == theme]

    def by_preset(self, preset_id: str) -> list[Asset]:
        """
        Return assets that list the given preset as compatible.
        An asset with an empty animation_compatible_presets list is considered
        compatible with *all* presets.
        """
        return [
            a for a in self._assets.values()
            if not a.animation_compatible_presets
            or preset_id in a.animation_compatible_presets
        ]

    def search(self, tag: str) -> list[Asset]:
        """Return assets whose tag list contains the given tag (case-insensitive)."""
        tag_lower = tag.lower()
        return [a for a in self._assets.values() if tag_lower in (t.lower() for t in a.tags)]

    def __len__(self) -> int:
        return len(self._assets)

    def __repr__(self) -> str:
        return f"AssetCatalog(path={self._path!r}, count={len(self._assets)})"

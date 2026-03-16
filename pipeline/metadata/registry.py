"""
pipeline/metadata/registry.py – Asset registry for MagicStix.

The registry loads :class:`~pipeline.asset_model.asset.Asset` objects from JSON
files stored under ``assets/source/<category>/``.  Each JSON file describes one
asset and uses the schema defined in ``docs/asset_schema.md``.

The registry is the single source of truth for what assets exist and which
motion presets they are compatible with.  The export pipeline and pack generator
both query it — nothing is hard-coded elsewhere.

File layout convention::

    assets/source/letters/letter_a_neon.json
    assets/source/letters/letter_b_neon.json
    assets/source/symbols/cloud_symbol.json
    ...

Each file must contain a valid ``Asset.from_dict()``-compatible JSON object.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from pipeline._paths import ASSETS_SOURCE_DIR
from pipeline.asset_model.asset import Asset

logger = logging.getLogger(__name__)

# Default location of source asset JSON descriptors.
_DEFAULT_SOURCE_DIR: Path = ASSETS_SOURCE_DIR


class AssetRegistry:
    """
    In-memory registry of all MagicStix base assets.

    On construction the registry scans *source_dir* for ``*.json`` files and
    loads each one as an :class:`~pipeline.asset_model.asset.Asset`.  Errors
    are logged and skipped so a single corrupt file never prevents startup.

    Usage::

        registry = AssetRegistry()
        letters = registry.get_by_category("letter")
        neon    = registry.get_by_theme("neon")
        asset   = registry.get("letter_a_neon")
    """

    def __init__(self, source_dir: Optional[str] = None) -> None:
        self._source_dir = Path(source_dir).resolve() if source_dir else _DEFAULT_SOURCE_DIR
        self._assets: Dict[str, Asset] = {}
        self._load()

    # ── Loading ───────────────────────────────────────────────

    def _load(self) -> None:
        """Scan *source_dir* recursively for ``*.json`` asset descriptors."""
        if not self._source_dir.is_dir():
            logger.warning(
                "Asset source directory not found: %s — registry will be empty.",
                self._source_dir,
            )
            return

        loaded = 0
        for path in self._source_dir.rglob("*.json"):
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                asset = Asset.from_dict(data)
                self._assets[asset.id] = asset
                loaded += 1
            except Exception as exc:
                logger.error("Failed to load asset from %s: %s", path, exc)

        logger.info("AssetRegistry: loaded %d asset(s) from %s", loaded, self._source_dir)

    def reload(self) -> None:
        """Clear and reload all assets from disk."""
        self._assets.clear()
        self._load()

    # ── Queries ───────────────────────────────────────────────

    def get(self, asset_id: str) -> Optional[Asset]:
        """Return the asset with *asset_id*, or ``None`` if not found."""
        return self._assets.get(asset_id)

    def all(self) -> List[Asset]:
        """Return all registered assets."""
        return list(self._assets.values())

    def get_by_category(self, category: str) -> List[Asset]:
        """Return assets whose ``category`` matches *category*."""
        return [a for a in self._assets.values() if a.category == category]

    def get_by_theme(self, theme: str) -> List[Asset]:
        """Return assets whose ``theme`` matches *theme*."""
        return [a for a in self._assets.values() if a.theme == theme]

    def get_by_tag(self, tag: str) -> List[Asset]:
        """Return assets that include *tag* in their ``tags`` list."""
        return [a for a in self._assets.values() if tag in a.tags]

    def get_compatible(self, preset_id: str) -> List[Asset]:
        """Return assets that are compatible with *preset_id*."""
        return [
            a for a in self._assets.values() if a.is_animation_compatible(preset_id)
        ]

    # ── Registration ──────────────────────────────────────────

    def register(self, asset: Asset) -> None:
        """Add or replace an asset in the in-memory registry."""
        self._assets[asset.id] = asset

    # ── Persistence ───────────────────────────────────────────

    def save(self, asset: Asset) -> str:
        """
        Persist *asset* as a JSON descriptor file.

        The file is written to
        ``<source_dir>/<category>/<asset_id>.json``.

        Returns the absolute path of the written file.
        """
        category_dir = self._source_dir / (asset.category + "s")
        category_dir.mkdir(parents=True, exist_ok=True)
        path = category_dir / f"{asset.id}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asset.to_dict(), fh, indent=2)
        self._assets[asset.id] = asset
        logger.info("Saved asset %s → %s", asset.id, path)
        return str(path)

    # ── Dunder ────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._assets)

    def __repr__(self) -> str:
        return f"<AssetRegistry assets={len(self._assets)} source_dir={str(self._source_dir)!r}>"

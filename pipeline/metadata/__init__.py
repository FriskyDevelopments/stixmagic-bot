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

import json
import logging
import os
from typing import Any

from pipeline.asset_model import Asset, AssetCategory, AssetTheme

logger = logging.getLogger(__name__)

DEFAULT_CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets", "catalog.json"
)

# Required fields that every asset record in catalog.json must contain.
_REQUIRED_ASSET_FIELDS: frozenset[str] = frozenset(
    {"id", "name", "category", "source_format", "source_path"}
)


class CatalogValidationError(ValueError):
    """Raised when a catalog file contains invalid or missing required fields."""


def _validate_raw_asset(raw: Any, index: int) -> None:
    """
    Validate a single raw asset dict from the catalog JSON.

    Raises :exc:`CatalogValidationError` with a descriptive message if any
    required field is absent or if a field value is not a string.

    Parameters
    ----------
    raw:
        The deserialized dict for one asset entry.
    index:
        Zero-based position in the catalog array (used in error messages).
    """
    if not isinstance(raw, dict):
        raise CatalogValidationError(
            f"Catalog entry [{index}] is not a JSON object (got {type(raw).__name__!r})."
        )

    missing = _REQUIRED_ASSET_FIELDS - raw.keys()
    if missing:
        asset_id = raw.get("id", f"<entry {index}>")
        raise CatalogValidationError(
            f"Asset {asset_id!r} (index {index}) is missing required "
            f"field(s): {sorted(missing)}"
        )

    for field in _REQUIRED_ASSET_FIELDS:
        if not isinstance(raw[field], str):
            raise CatalogValidationError(
                f"Asset {raw['id']!r} (index {index}): field {field!r} must be a "
                f"string, got {type(raw[field]).__name__!r}."
            )

    if not raw["id"].strip():
        raise CatalogValidationError(
            f"Catalog entry [{index}] has an empty 'id' field."
        )


class AssetCatalog:
    """
    In-memory asset registry backed by a JSON file.

    The catalog is lazily loaded; call :meth:`load` explicitly or pass
    ``auto_load=True`` to ``__init__``.

    Catalog schema validation
    -------------------------
    :meth:`load` validates every entry against the required-field schema.
    Pass ``strict=True`` to :meth:`load` to raise :exc:`CatalogValidationError`
    on the first invalid entry (default is to log the error and skip the
    offending entry so that a partially valid catalog is still usable).
    """

    def __init__(
        self, path: str = DEFAULT_CATALOG_PATH, *, auto_load: bool = False
    ) -> None:
        self._path = os.path.abspath(path)
        self._assets: dict[str, Asset] = {}
        if auto_load and os.path.exists(self._path):
            self.load()

    # ── Persistence ───────────────────────────────────────────

    def load(self, *, strict: bool = False) -> None:
        """
        Load / reload the catalog from disk.

        Missing file is treated as an empty catalog.

        Parameters
        ----------
        strict:
            When True, raise :exc:`CatalogValidationError` on the first
            invalid entry.  When False (default), log the error and skip the
            offending entry so the rest of the catalog is still available.
        """
        raw = self._read_catalog_file(strict)
        if raw is None:
            return

        self._assets = self._parse_assets(raw, strict)
        logger.info(
            "Loaded %d assets from catalog (%d entries in file).",
            len(self._assets),
            len(raw),
        )

    def _read_catalog_file(self, strict: bool) -> list[dict[str, Any]] | None:
        if not os.path.exists(self._path):
            logger.info("Catalog not found at %s — starting empty.", self._path)
            return None
        try:
            with open(self._path, encoding="utf-8") as fh:
                raw: list[dict[str, Any]] = json.load(fh)
        except json.JSONDecodeError as exc:
            msg = f"Catalog at {self._path} is not valid JSON: {exc}"
            if strict:
                raise CatalogValidationError(msg) from exc
            logger.error(msg)
            return None
        except Exception as exc:
            logger.error("Failed to open catalog %s: %s", self._path, exc)
            return None

        if not isinstance(raw, list):
            msg = (
                f"Catalog at {self._path} must be a JSON array, "
                f"got {type(raw).__name__!r}."
            )
            if strict:
                raise CatalogValidationError(msg)
            logger.error(msg)
            return None

        return raw

    def _parse_assets(
        self, raw: list[dict[str, Any]], strict: bool
    ) -> dict[str, Asset]:
        loaded: dict[str, Asset] = {}
        for i, item in enumerate(raw):
            try:
                _validate_raw_asset(item, i)
                asset = Asset.from_dict(item)
            except (CatalogValidationError, ValueError, KeyError) as exc:
                if strict:
                    raise CatalogValidationError(str(exc)) from exc
                logger.error(
                    "Catalog entry [%d] skipped due to validation error: %s", i, exc
                )
                continue
            loaded[asset.id] = asset
        return loaded

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
            a
            for a in self._assets.values()
            if not a.animation_compatible_presets
            or preset_id in a.animation_compatible_presets
        ]

    def search(self, tag: str) -> list[Asset]:
        """Return assets whose tag list contains the given tag (case-insensitive)."""
        tag_lower = tag.lower()
        return [
            a for a in self._assets.values() if tag_lower in (t.lower() for t in a.tags)
        ]

    def __len__(self) -> int:
        return len(self._assets)

    def __repr__(self) -> str:
        return f"AssetCatalog(path={self._path!r}, count={len(self._assets)})"


# ── AssetRegistry alias ───────────────────────────────────────
# registry.py provides a file-scan-based registry as an alternative to the
# JSON-catalog approach above.  Both are exposed from this package.
try:
    from .registry import AssetRegistry  # noqa: F401
except ImportError:
    pass

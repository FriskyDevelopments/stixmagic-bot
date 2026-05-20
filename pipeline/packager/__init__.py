"""
pipeline/packager/__init__.py – MagicStix pack assembly and metadata.

A Pack groups a set of assets and motion presets under a themed product
bundle, and describes which export formats should be included.

Pack definitions live in ``packs/<pack_id>/pack.json``.  The
:class:`PackDefinition` dataclass mirrors that schema; :func:`build_pack`
walks the asset catalog and produces a manifest of every expected output
file.

Usage
-----
>>> from pipeline.packager import PackDefinition, build_pack
>>> from pipeline.metadata import AssetCatalog
>>> from pipeline.motion_presets import get_preset
>>>
>>> catalog = AssetCatalog(auto_load=True)
>>> pack = PackDefinition.from_file("packs/motion_alphabet/pack.json")
>>> manifest = build_pack(pack, catalog)
>>> print(manifest)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from pipeline.asset_model import Asset

logger = logging.getLogger(__name__)


class PackValidationError(ValueError):
    """Raised when a pack definition references unknown assets or presets."""


# ── PackDefinition ────────────────────────────────────────────

@dataclass
class PackDefinition:
    """
    Metadata definition for a distributable asset pack.

    Parameters
    ----------
    pack_id:
        Unique slug (e.g. ``"motion_alphabet"``).
    title:
        Human-readable pack name.
    theme:
        Stylistic theme (e.g. ``"neon"``, ``"cloud"``).
    included_assets:
        List of asset id slugs included in this pack.
        An empty list means *all* assets in the catalog are included.
    included_motion_presets:
        List of motion preset id slugs to apply to each included asset.
    export_formats:
        Formats to export (e.g. ``["gif", "webp", "webm", "thumbnail"]``).
    target_platforms:
        Where these assets are intended to be used
        (e.g. ``["telegram", "obs", "browser_extension"]``).
    use_cases:
        Free-form list of use-case descriptions.
    notes:
        Free-form remarks.
    """

    pack_id: str
    title: str
    theme: str = ""
    included_assets: list[str] = field(default_factory=list)
    included_motion_presets: list[str] = field(default_factory=list)
    export_formats: list[str] = field(default_factory=lambda: ["gif", "webp", "webm", "thumbnail"])
    target_platforms: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "title": self.title,
            "theme": self.theme,
            "included_assets": self.included_assets,
            "included_motion_presets": self.included_motion_presets,
            "export_formats": self.export_formats,
            "target_platforms": self.target_platforms,
            "use_cases": self.use_cases,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PackDefinition":
        return cls(
            pack_id=data["pack_id"],
            title=data["title"],
            theme=data.get("theme", ""),
            included_assets=data.get("included_assets", []),
            included_motion_presets=data.get("included_motion_presets", []),
            export_formats=data.get("export_formats", ["gif", "webp", "webm", "thumbnail"]),
            target_platforms=data.get("target_platforms", []),
            use_cases=data.get("use_cases", []),
            notes=data.get("notes", ""),
        )

    @classmethod
    def from_file(cls, path: str) -> "PackDefinition":
        """Load a PackDefinition from a ``pack.json`` file."""
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def save(self, path: str) -> None:
        """Persist this PackDefinition to a ``pack.json`` file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)


# ── PackManifest ──────────────────────────────────────────────

@dataclass
class PackManifestEntry:
    """One row in a pack build manifest."""
    asset_id: str
    preset_id: str
    expected_outputs: dict[str, str]  # format → expected output path


@dataclass
class PackManifest:
    """The full set of expected outputs for a pack build."""
    pack_id: str
    entries: list[PackManifestEntry] = field(default_factory=list)

    def summary(self) -> str:
        total = sum(len(e.expected_outputs) for e in self.entries)
        return (
            f"Pack '{self.pack_id}': "
            f"{len(self.entries)} asset×preset combinations, "
            f"{total} total expected output files."
        )


# ── Validation helper ─────────────────────────────────────────

def validate_pack(
    pack: PackDefinition,
    catalog: Any,  # pipeline.metadata.AssetCatalog
    *,
    strict: bool = True,
) -> list[str]:
    """
    Validate that all assets and presets referenced by *pack* exist.

    Parameters
    ----------
    pack:
        The pack definition to validate.
    catalog:
        A loaded :class:`~pipeline.metadata.AssetCatalog` instance.
    strict:
        When True (default), raise :exc:`PackValidationError` if any
        referenced asset or preset is missing.
        When False, return the list of error strings without raising.

    Returns
    -------
    list[str]
        Empty list when valid.  Contains one error string per missing
        asset or preset when ``strict=False``.

    Raises
    ------
    PackValidationError
        When ``strict=True`` and any referenced asset or preset is not found.
    """
    from pipeline.motion_presets import PRESET_REGISTRY

    errors: list[str] = []

    for asset_id in pack.included_assets:
        if catalog.get(asset_id) is None:
            errors.append(
                f"Pack '{pack.pack_id}': asset '{asset_id}' not found in catalog."
            )

    for preset_id in pack.included_motion_presets:
        if preset_id not in PRESET_REGISTRY:
            errors.append(
                f"Pack '{pack.pack_id}': motion preset '{preset_id}' not found in preset registry."
            )

    if errors:
        for err in errors:
            logger.warning(err)
        if strict:
            raise PackValidationError("\n".join(errors))

    return errors


# ── Build helper ──────────────────────────────────────────────



def _resolve_assets(pack: PackDefinition, catalog: Any) -> list[Asset]:
    """Resolve the list of assets included in the pack."""
    if pack.included_assets:
        # ⚡ Bolt Optimization: Cache dictionary/method lookup before loop
        # Impact: Reduces O(N) attribute lookups during list comprehension
        get_asset = catalog.get
        return [
            a for aid in pack.included_assets
            if (a := get_asset(aid)) is not None
        ]
    return catalog.all()


def _resolve_presets(pack: PackDefinition) -> list[Any]:
    """Resolve the list of motion presets included in the pack."""
    from pipeline.motion_presets import get_preset, BUILTIN_PRESETS
    if pack.included_motion_presets:
        # ⚡ Bolt Optimization: Cache method lookup before loop
        # Impact: Reduces O(N) name lookups during list comprehension
        get_pre = get_preset
        return [p for pid in pack.included_motion_presets if (p := get_pre(pid)) is not None]
    return list(BUILTIN_PRESETS)


def _build_entries(pack: PackDefinition, assets: list[Asset], presets: list[Any], renders_root: str) -> list[PackManifestEntry]:
    """Generate the expected outputs for all asset/preset combinations."""
    _dir_map = {
        "gif":          os.path.join(renders_root, "gif"),
        "webp":         os.path.join(renders_root, "webp"),
        "webm":         os.path.join(renders_root, "webm"),
        "mov":          os.path.join(renders_root, "mov"),
        "png_sequence": os.path.join(renders_root, "png_sequences"),
        "thumbnail":    os.path.join(renders_root, "thumbnails"),
    }
    _ext_map = {
        "gif": "gif", "webp": "webp", "webm": "webm",
        "mov": "mov", "thumbnail": "png",
    }

    # ⚡ Bolt Optimization: Pre-compute formats and loop invariants
    # Impact: Reduces O(Assets * Presets * Formats) dictionary lookups and path building
    has_thumb = "thumbnail" in pack.export_formats
    has_seq = "png_sequence" in pack.export_formats
    thumb_dir = _dir_map.get("thumbnail")
    seq_dir = _dir_map.get("png_sequence")

    other_formats = [
        (fmt, _ext_map.get(fmt, fmt), _dir_map[fmt])
        for fmt in pack.export_formats
        if fmt not in ("thumbnail", "png_sequence") and fmt in _dir_map
    ]

    entries: list[PackManifestEntry] = []
    for asset in assets:
        asset_id = asset.id
        # Thumbnail only depends on the asset, not the preset
        thumb_path = os.path.join(thumb_dir, f"{asset_id}_thumb.png") if has_thumb and thumb_dir else None

        for preset in presets:
            preset_id = preset.id
            outputs: dict[str, str] = {}
            if has_thumb and thumb_path:
                outputs["thumbnail"] = thumb_path
            if has_seq and seq_dir:
                outputs["png_sequence"] = os.path.join(seq_dir, f"{asset_id}_{preset_id}_frames")
            for fmt, ext, fdir in other_formats:
                outputs[fmt] = os.path.join(fdir, f"{asset_id}_{preset_id}.{ext}")
            entries.append(PackManifestEntry(asset_id=asset_id, preset_id=preset_id, expected_outputs=outputs))
    return entries


def build_pack(
    pack: PackDefinition,
    catalog: Any,  # pipeline.metadata.AssetCatalog
    *,
    renders_root: str = "renders",
    strict_validation: bool = True,
) -> PackManifest:
    """
    Compute the expected output manifest for a pack without running exporters.

    This function drives pack assembly from metadata alone: it resolves which
    assets and presets are involved, then lists every output file path that
    the exporters would produce.

    Parameters
    ----------
    pack:
        The pack definition to build.
    catalog:
        An :class:`~pipeline.metadata.AssetCatalog` instance (already loaded).
    renders_root:
        Root directory used to compute expected output paths.
    strict_validation:
        When True (default), raise :exc:`PackValidationError` if any
        referenced asset or preset is not found.  When False, missing
        references are logged as warnings and skipped.

    Returns
    -------
    PackManifest
        Contains one :class:`PackManifestEntry` per asset × preset combination.

    Raises
    ------
    PackValidationError
        When ``strict_validation=True`` and an invalid reference is found.
    """
    # Validate referenced assets and presets before building the manifest
    validate_pack(pack, catalog, strict=strict_validation)

    assets = _resolve_assets(pack, catalog)
    presets = _resolve_presets(pack)

    manifest = PackManifest(pack_id=pack.pack_id)
    manifest.entries = _build_entries(pack, assets, presets, renders_root)

    logger.info("build_pack: %s", manifest.summary())
    return manifest


# ── OOP pack generator ────────────────────────────────────────
# pack.py and generator.py provide a class-based alternative to the
# functional PackDefinition / build_pack API above.
try:
    from .pack import Pack  # noqa: F401
    from .generator import PackGenerator  # noqa: F401
except ImportError:
    pass

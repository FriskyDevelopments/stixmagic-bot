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


# ── Build helper ──────────────────────────────────────────────

def build_pack(
    pack: PackDefinition,
    catalog: Any,  # pipeline.metadata.AssetCatalog
    *,
    renders_root: str = "renders",
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

    Returns
    -------
    PackManifest
        Contains one :class:`PackManifestEntry` per asset × preset combination.
    """
    from pipeline.motion_presets import get_preset, BUILTIN_PRESETS

    # Resolve assets
    if pack.included_assets:
        assets: list[Asset] = [
            a for aid in pack.included_assets
            if (a := catalog.get(aid)) is not None
        ]
    else:
        assets = catalog.all()

    # Resolve presets
    if pack.included_motion_presets:
        presets = [p for pid in pack.included_motion_presets if (p := get_preset(pid)) is not None]
    else:
        presets = list(BUILTIN_PRESETS)

    manifest = PackManifest(pack_id=pack.pack_id)

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

    for asset in assets:
        for preset in presets:
            outputs: dict[str, str] = {}
            for fmt in pack.export_formats:
                if fmt == "thumbnail":
                    outputs["thumbnail"] = os.path.join(
                        _dir_map["thumbnail"], f"{asset.id}_thumb.png"
                    )
                elif fmt == "png_sequence":
                    outputs["png_sequence"] = os.path.join(
                        _dir_map["png_sequence"], f"{asset.id}_{preset.id}_frames"
                    )
                elif fmt in _dir_map:
                    ext = _ext_map.get(fmt, fmt)
                    outputs[fmt] = os.path.join(
                        _dir_map[fmt], f"{asset.id}_{preset.id}.{ext}"
                    )
            manifest.entries.append(
                PackManifestEntry(
                    asset_id=asset.id,
                    preset_id=preset.id,
                    expected_outputs=outputs,
                )
            )

    logger.info("build_pack: %s", manifest.summary())
    return manifest

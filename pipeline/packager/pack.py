"""
pipeline/packager/pack.py – Pack data model for MagicStix product packs.

A Pack groups a set of base assets and motion presets together, describes
the target platforms and export formats, and is the basis for the automated
pack generation system.

Pack descriptors live under ``packs/<pack_id>/pack.json`` and are loaded by
:class:`~pipeline.packager.generator.PackGenerator`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Pack:
    """
    Describes a MagicStix product pack.

    Attributes:
        pack_id:                 Unique identifier (e.g. ``"motion_alphabet"``).
        title:                   Human-readable display title.
        theme:                   Visual theme of the pack (e.g. ``"neon"``).
        included_assets:         List of asset IDs to include.
        included_motion_presets: List of preset IDs to apply to every asset.
        export_formats:          Target output formats (e.g. ``["gif", "webp"]``).
        target_platforms:        Deployment targets (e.g. ``["telegram", "overlay"]``).
        use_cases:               High-level use-case labels (e.g. ``["sticker", "stream_overlay"]``).
        description:             Human-readable pack description.
    """

    pack_id: str
    title: str
    theme: str = "abstract"
    included_assets: List[str] = field(default_factory=list)
    included_motion_presets: List[str] = field(default_factory=list)
    export_formats: List[str] = field(default_factory=list)
    target_platforms: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    description: str = ""

    # ── Serialisation ─────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "pack_id": self.pack_id,
            "title": self.title,
            "theme": self.theme,
            "included_assets": self.included_assets,
            "included_motion_presets": self.included_motion_presets,
            "export_formats": self.export_formats,
            "target_platforms": self.target_platforms,
            "use_cases": self.use_cases,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pack":
        return cls(
            pack_id=data["pack_id"],
            title=data["title"],
            theme=data.get("theme", "abstract"),
            included_assets=data.get("included_assets", []),
            included_motion_presets=data.get("included_motion_presets", []),
            export_formats=data.get("export_formats", []),
            target_platforms=data.get("target_platforms", []),
            use_cases=data.get("use_cases", []),
            description=data.get("description", ""),
        )

    def __repr__(self) -> str:
        return (
            f"<Pack pack_id={self.pack_id!r} title={self.title!r} "
            f"assets={len(self.included_assets)} presets={len(self.included_motion_presets)}>"
        )

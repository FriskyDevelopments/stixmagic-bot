"""
pipeline/asset_model/__init__.py – MagicStix asset data model.

Defines the Asset dataclass that describes every base visual element in
the pipeline, plus the AssetCategory and AssetTheme enumerations used for
filtering and pack assembly.

One asset record travels through the entire pipeline and drives which motion
presets, export targets, and packs it participates in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────


class AssetCategory(str, Enum):
    LETTER   = "letter"
    NUMBER   = "number"
    EMOJI    = "emoji"
    SIGNAL   = "signal"
    FRAME    = "frame"
    PARTICLE = "particle"
    ICON     = "icon"
    STICKER  = "sticker"
    OVERLAY  = "overlay_element"
    SYMBOL   = "symbol"


class AssetTheme(str, Enum):
    NEON     = "neon"
    CLOUD    = "cloud"
    SIGNAL   = "signal"
    DJ       = "dj"
    CLUB     = "club"
    HOST     = "host"
    TRADING  = "trading"
    ABSTRACT = "abstract"


class SourceFormat(str, Enum):
    PNG  = "png"
    SVG  = "svg"
    WEBP = "webp"
    GIF  = "gif"
    WEBM = "webm"


# ── Asset dataclass ───────────────────────────────────────────


@dataclass
class Asset:
    """
    Canonical description of a single base visual asset.

    This record is the single source of truth that drives the entire
    rendering and pack-assembly pipeline.  Every field has a sensible
    default so callers only need to supply the mandatory identifiers.

    Parameters
    ----------
    id:
        Unique slug (e.g. ``"letter_A"``, ``"symbol_cloud"``).
    name:
        Human-readable label (e.g. ``"Letter A"``, ``"Cloud Symbol"``).
    category:
        One of the AssetCategory members.
    source_format:
        File format of the raw source file stored under ``assets/source/``.
    source_path:
        Relative path from the repo root to the source file.
    width / height:
        Native pixel dimensions of the source asset.
    transparent_background:
        True when the asset already has an alpha channel.
    theme:
        Optional stylistic theme tag.
    tags:
        Free-form keyword list for search / grouping.
    animation_compatible_presets:
        IDs of MotionPreset instances known to work well with this asset.
        An empty list means *all* presets are allowed.
    export_targets:
        Explicit list of format strings this asset should be exported to
        (e.g. ``["gif", "webp", "webm"]``).  Empty list = use pack default.
    notes:
        Free-form remarks for pipeline operators.
    """

    id: str
    name: str
    category: AssetCategory
    source_format: SourceFormat
    source_path: str

    width: int = 512
    height: int = 512
    transparent_background: bool = True

    theme: AssetTheme | None = None
    tags: list[str] = field(default_factory=list)
    animation_compatible_presets: list[str] = field(default_factory=list)
    export_targets: list[str] = field(default_factory=list)
    notes: str = ""

    # ── Helpers ───────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary (suitable for JSON persistence)."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "source_format": self.source_format.value,
            "source_path": self.source_path,
            "width": self.width,
            "height": self.height,
            "transparent_background": self.transparent_background,
            "theme": self.theme.value if self.theme else None,
            "tags": self.tags,
            "animation_compatible_presets": self.animation_compatible_presets,
            "export_targets": self.export_targets,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Asset":
        """Deserialise from a plain dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            category=AssetCategory(data["category"]),
            source_format=SourceFormat(data["source_format"]),
            source_path=data["source_path"],
            width=data.get("width", 512),
            height=data.get("height", 512),
            transparent_background=data.get("transparent_background", True),
            theme=AssetTheme(data["theme"]) if data.get("theme") else None,
            tags=data.get("tags", []),
            animation_compatible_presets=data.get("animation_compatible_presets", []),
            export_targets=data.get("export_targets", []),
            notes=data.get("notes", ""),
        )

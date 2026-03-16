"""
pipeline/asset_model/asset.py – Core Asset data model for MagicStix.

An Asset represents a single visual element (letter, emoji, symbol, …) that can
be fed into the motion/export pipeline to produce multiple output formats.

One base asset  +  one motion preset  →  multiple export files
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# ── Asset categories ──────────────────────────────────────────

CATEGORY_LETTER = "letter"
CATEGORY_NUMBER = "number"
CATEGORY_EMOJI = "emoji"
CATEGORY_SIGNAL = "signal"
CATEGORY_FRAME = "frame"
CATEGORY_PARTICLE = "particle"
CATEGORY_ICON = "icon"
CATEGORY_STICKER = "sticker"
CATEGORY_OVERLAY_ELEMENT = "overlay_element"
CATEGORY_SYMBOL = "symbol"

ALL_CATEGORIES = [
    CATEGORY_LETTER,
    CATEGORY_NUMBER,
    CATEGORY_EMOJI,
    CATEGORY_SIGNAL,
    CATEGORY_FRAME,
    CATEGORY_PARTICLE,
    CATEGORY_ICON,
    CATEGORY_STICKER,
    CATEGORY_OVERLAY_ELEMENT,
    CATEGORY_SYMBOL,
]

# ── Asset themes ──────────────────────────────────────────────

THEME_NEON = "neon"
THEME_CLOUD = "cloud"
THEME_SIGNAL = "signal"
THEME_DJ = "dj"
THEME_CLUB = "club"
THEME_HOST = "host"
THEME_TRADING = "trading"
THEME_ABSTRACT = "abstract"

ALL_THEMES = [
    THEME_NEON,
    THEME_CLOUD,
    THEME_SIGNAL,
    THEME_DJ,
    THEME_CLUB,
    THEME_HOST,
    THEME_TRADING,
    THEME_ABSTRACT,
]

# ── Source formats ────────────────────────────────────────────

FORMAT_PNG = "png"
FORMAT_SVG = "svg"
FORMAT_WEBP = "webp"

# ── Export targets ────────────────────────────────────────────

EXPORT_GIF = "gif"
EXPORT_ANIMATED_WEBP = "animated_webp"
EXPORT_WEBM = "webm"
EXPORT_MOV = "mov"
EXPORT_PNG_SEQUENCE = "png_sequence"
EXPORT_THUMBNAIL = "thumbnail"

ALL_EXPORT_TARGETS = [
    EXPORT_GIF,
    EXPORT_ANIMATED_WEBP,
    EXPORT_WEBM,
    EXPORT_MOV,
    EXPORT_PNG_SEQUENCE,
    EXPORT_THUMBNAIL,
]


# ── Asset dataclass ───────────────────────────────────────────

@dataclass
class Asset:
    """
    Represents a single MagicStix base asset.

    Base assets are the raw inputs for the export pipeline.
    One asset can produce multiple outputs by pairing with motion presets.

    Attributes:
        id:                             Unique identifier (e.g. ``"letter_a_neon"``).
        name:                           Human-readable display name.
        category:                       One of the ``CATEGORY_*`` constants.
        theme:                          One of the ``THEME_*`` constants.
        source_format:                  One of the ``FORMAT_*`` constants.
        source_path:                    Relative path inside ``assets/source/``.
        width:                          Source image width in pixels.
        height:                         Source image height in pixels.
        transparent_background:         True when the source has an alpha channel.
        tags:                           Free-form labels for search and grouping.
        animation_compatible_presets:   Preset IDs that work well with this asset.
                                        Empty list means all presets are compatible.
        export_targets:                 Output formats this asset should produce.
                                        Empty list means all formats are enabled.
        notes:                          Free-form notes for pipeline operators.
    """

    id: str
    name: str
    category: str
    theme: str
    source_format: str
    source_path: str
    width: int
    height: int
    transparent_background: bool = True
    tags: List[str] = field(default_factory=list)
    animation_compatible_presets: List[str] = field(default_factory=list)
    export_targets: List[str] = field(default_factory=list)
    notes: str = ""

    # ── Helpers ───────────────────────────────────────────────

    def is_animation_compatible(self, preset_id: str) -> bool:
        """Return True if this asset supports the given motion preset."""
        return (
            not self.animation_compatible_presets
            or preset_id in self.animation_compatible_presets
        )

    def supports_export(self, export_target: str) -> bool:
        """Return True if this asset should be exported to *export_target*."""
        return not self.export_targets or export_target in self.export_targets

    # ── Serialisation ─────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON metadata files."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "theme": self.theme,
            "source_format": self.source_format,
            "source_path": self.source_path,
            "width": self.width,
            "height": self.height,
            "transparent_background": self.transparent_background,
            "tags": self.tags,
            "animation_compatible_presets": self.animation_compatible_presets,
            "export_targets": self.export_targets,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Asset":
        """Deserialize from a plain dict (e.g. loaded from a JSON metadata file)."""
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            theme=data["theme"],
            source_format=data["source_format"],
            source_path=data["source_path"],
            width=data["width"],
            height=data["height"],
            transparent_background=data.get("transparent_background", True),
            tags=data.get("tags", []),
            animation_compatible_presets=data.get("animation_compatible_presets", []),
            export_targets=data.get("export_targets", []),
            notes=data.get("notes", ""),
        )

    def __repr__(self) -> str:
        return f"<Asset id={self.id!r} category={self.category!r} theme={self.theme!r}>"

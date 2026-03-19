"""
pipeline/motion_presets/__init__.py – MagicStix motion preset registry.

Defines the MotionPreset dataclass and the built-in preset catalogue.
Presets are deliberately abstract: they describe *what* an animation
should feel like and constrain which asset categories and export formats
are appropriate.  Actual rendering is delegated to the exporters layer.

Built-in presets
----------------
pulse, glow, wobble, bounce, orbit, glitch, sparkle,
particle_burst, laser_sweep, signal_flash
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── MotionPreset dataclass ────────────────────────────────────


@dataclass
class MotionPreset:
    """
    Reusable animation preset consumed by the export pipeline.

    Parameters
    ----------
    id:
        Unique slug used as part of output filenames
        (e.g. ``"pulse"`` → ``letter_A_pulse.gif``).
    name:
        Human-readable label.
    loopable:
        True when the animation is designed to loop seamlessly.
    duration:
        Total animation duration in seconds.
    alpha_safe:
        True when the effect preserves the source alpha channel.
    overlay_safe:
        True when the output is suitable for transparent overlay use-cases.
    sticker_safe:
        True when the output meets Telegram sticker constraints.
    recommended_categories:
        Asset category IDs this preset works best with.
        An empty list means *all* categories are compatible.
    parameter_schema:
        Optional dict describing tweakable parameters for this preset
        (e.g. speed, intensity, colour).  Intended for future UI tooling.
    notes:
        Free-form remarks.
    """

    id: str
    name: str
    loopable: bool = True
    duration: float = 2.0
    alpha_safe: bool = True
    overlay_safe: bool = True
    sticker_safe: bool = True
    recommended_categories: list[str] = field(default_factory=list)
    parameter_schema: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "loopable": self.loopable,
            "duration": self.duration,
            "alpha_safe": self.alpha_safe,
            "overlay_safe": self.overlay_safe,
            "sticker_safe": self.sticker_safe,
            "recommended_categories": self.recommended_categories,
            "parameter_schema": self.parameter_schema,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MotionPreset":
        return cls(
            id=data["id"],
            name=data["name"],
            loopable=data.get("loopable", True),
            duration=data.get("duration", 2.0),
            alpha_safe=data.get("alpha_safe", True),
            overlay_safe=data.get("overlay_safe", True),
            sticker_safe=data.get("sticker_safe", True),
            recommended_categories=data.get("recommended_categories", []),
            parameter_schema=data.get("parameter_schema", {}),
            notes=data.get("notes", ""),
        )


# ── Built-in preset catalogue ─────────────────────────────────

BUILTIN_PRESETS: list[MotionPreset] = [
    MotionPreset(
        id="pulse",
        name="Pulse",
        loopable=True,
        duration=1.5,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["letter", "number", "symbol", "icon"],
        parameter_schema={
            "scale_min": {"type": "float", "default": 0.9, "min": 0.5, "max": 1.0},
            "scale_max": {"type": "float", "default": 1.1, "min": 1.0, "max": 2.0},
            "easing":    {"type": "string", "default": "ease_in_out"},
        },
        notes="Simple scale-in/scale-out loop.  Works on any category.",
    ),
    MotionPreset(
        id="glow",
        name="Glow",
        loopable=True,
        duration=2.0,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["letter", "signal", "icon", "symbol"],
        parameter_schema={
            "color":     {"type": "string",  "default": "#ffffff"},
            "intensity": {"type": "float",   "default": 0.8, "min": 0.0, "max": 1.0},
            "radius":    {"type": "integer", "default": 10,  "min": 1,   "max": 40},
        },
        notes="Gaussian-blur halo fades in and out around the asset.",
    ),
    MotionPreset(
        id="wobble",
        name="Wobble",
        loopable=True,
        duration=1.0,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["emoji", "icon", "sticker"],
        parameter_schema={
            "angle":     {"type": "float",   "default": 10.0, "min": 1.0, "max": 45.0},
            "frequency": {"type": "float",   "default": 2.0,  "min": 0.5, "max": 5.0},
        },
        notes="Left-right rotation shake.  Great for emoji reactions.",
    ),
    MotionPreset(
        id="bounce",
        name="Bounce",
        loopable=True,
        duration=1.2,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["emoji", "letter", "number"],
        parameter_schema={
            "height": {"type": "integer", "default": 20, "min": 5, "max": 100},
            "decay":  {"type": "float",   "default": 0.5, "min": 0.0, "max": 1.0},
        },
        notes="Vertical bounce with optional decay (elastic feel).",
    ),
    MotionPreset(
        id="orbit",
        name="Orbit",
        loopable=True,
        duration=3.0,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=False,
        recommended_categories=["particle", "symbol", "overlay_element"],
        parameter_schema={
            "radius":    {"type": "integer", "default": 30, "min": 10, "max": 200},
            "num_items": {"type": "integer", "default": 4,  "min": 1,  "max": 12},
        },
        notes="Small child elements revolve around the main asset.  "
              "Not sticker_safe because it requires extra canvas space.",
    ),
    MotionPreset(
        id="glitch",
        name="Glitch",
        loopable=True,
        duration=2.0,
        alpha_safe=False,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["letter", "signal", "icon"],
        parameter_schema={
            "intensity":  {"type": "float",   "default": 0.6, "min": 0.1, "max": 1.0},
            "slice_count": {"type": "integer", "default": 5,   "min": 2,   "max": 20},
        },
        notes="RGB-split / horizontal-slice glitch effect.  "
              "alpha_safe=False because channel splitting may alter transparency.",
    ),
    MotionPreset(
        id="sparkle",
        name="Sparkle",
        loopable=True,
        duration=2.5,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["symbol", "frame", "sticker", "overlay_element"],
        parameter_schema={
            "num_particles": {"type": "integer", "default": 8,  "min": 2,  "max": 30},
            "color":         {"type": "string",  "default": "#ffdd00"},
            "size_range":    {"type": "array",   "default": [2, 8]},
        },
        notes="Small star / sparkle particles burst from the asset edges.",
    ),
    MotionPreset(
        id="particle_burst",
        name="Particle Burst",
        loopable=False,
        duration=1.5,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=False,
        recommended_categories=["particle", "symbol", "emoji"],
        parameter_schema={
            "count":    {"type": "integer", "default": 20, "min": 5, "max": 100},
            "spread":   {"type": "float",   "default": 1.0, "min": 0.2, "max": 3.0},
            "fade_out": {"type": "boolean", "default": True},
        },
        notes="Single non-looping burst of particles.  Not sticker_safe "
              "as Telegram animated stickers must loop.",
    ),
    MotionPreset(
        id="laser_sweep",
        name="Laser Sweep",
        loopable=True,
        duration=2.0,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["signal", "frame", "overlay_element"],
        parameter_schema={
            "direction": {"type": "string", "default": "left_to_right",
                          "options": ["left_to_right", "right_to_left", "top_to_bottom"]},
            "color":     {"type": "string", "default": "#00ffff"},
            "width":     {"type": "integer", "default": 4, "min": 1, "max": 20},
        },
        notes="A bright scan-line sweeps across the asset.",
    ),
    MotionPreset(
        id="signal_flash",
        name="Signal Flash",
        loopable=True,
        duration=0.8,
        alpha_safe=True,
        overlay_safe=True,
        sticker_safe=True,
        recommended_categories=["signal", "icon", "overlay_element"],
        parameter_schema={
            "on_frames":  {"type": "integer", "default": 3, "min": 1, "max": 10},
            "off_frames": {"type": "integer", "default": 3, "min": 1, "max": 10},
            "color":      {"type": "string",  "default": "#ff0000"},
        },
        notes="Rapid on/off blink reminiscent of a signal indicator light.",
    ),
]

# Keyed lookup for convenient access by ID
PRESET_REGISTRY: dict[str, MotionPreset] = {p.id: p for p in BUILTIN_PRESETS}


def get_preset(preset_id: str) -> MotionPreset | None:
    """Return the MotionPreset with the given id, or None if not found."""
    return PRESET_REGISTRY.get(preset_id)


def list_presets(
    *,
    category: str | None = None,
    sticker_safe: bool | None = None,
    overlay_safe: bool | None = None,
) -> list[MotionPreset]:
    """
    Return presets filtered by optional criteria.

    Parameters
    ----------
    category:
        If provided, only return presets whose recommended_categories list
        contains this category string, or whose list is empty (= all).
    sticker_safe:
        Filter by the sticker_safe flag when not None.
    overlay_safe:
        Filter by the overlay_safe flag when not None.
    """
    result = list(BUILTIN_PRESETS)

    if category is not None:
        result = [
            p for p in result
            if not p.recommended_categories or category in p.recommended_categories
        ]
    if sticker_safe is not None:
        result = [p for p in result if p.sticker_safe is sticker_safe]
    if overlay_safe is not None:
        result = [p for p in result if p.overlay_safe is overlay_safe]

    return result


# ── Catalog helpers ───────────────────────────────────────────
# catalog.py and preset.py provide a dict-based preset registry that wraps
# the dataclass above.  Both APIs are exposed from this package.
try:
    from .catalog import PRESETS, get_preset as _catalog_get_preset, list_presets  # noqa: F401
except ImportError:
    pass

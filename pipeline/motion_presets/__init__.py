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

# ── Catalog helpers ───────────────────────────────────────────
# catalog.py and preset.py provide a dict-based preset registry that wraps
# the dataclass above.  Both APIs are exposed from this package.
try:
    from .catalog import PRESETS
    from .catalog import get_preset as _catalog_get_preset
    from .preset import MotionPreset

    PRESET_REGISTRY = PRESETS
    BUILTIN_PRESETS = list(PRESETS.values())
except ImportError:
    pass


def get_preset(preset_id: str) -> MotionPreset | None:
    """Return the MotionPreset with the given id, or None if not found."""
    try:
        return _catalog_get_preset(preset_id)
    except KeyError:
        return None


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
            p
            for p in result
            if not p.recommended_categories or category in p.recommended_categories
        ]
    if sticker_safe is not None:
        result = [p for p in result if p.sticker_safe is sticker_safe]
    if overlay_safe is not None:
        result = [p for p in result if p.overlay_safe is overlay_safe]

    return result

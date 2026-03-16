"""
pipeline/motion_presets/catalog.py – Built-in motion preset catalog.

This module defines the ten initial MagicStix motion presets.  All presets are
held in the ``PRESETS`` dict keyed by their ``id`` string.

Adding a new preset
-------------------
1. Instantiate a :class:`~pipeline.motion_presets.preset.MotionPreset` below.
2. Add it to ``PRESETS``.
3. Add rendering logic in the relevant exporter (``pipeline/exporters/``).
4. Update ``docs/motion_system.md``.
"""

from __future__ import annotations

from typing import Dict

from pipeline.motion_presets.preset import MotionPreset

# ── Built-in presets ──────────────────────────────────────────

_PULSE = MotionPreset(
    id="pulse",
    name="Pulse",
    loopable=True,
    duration_ms=800,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["letter", "number", "emoji", "icon", "sticker"],
    parameter_schema={
        "scale_min": {"type": "number", "default": 0.9, "min": 0.5, "max": 1.0},
        "scale_max": {"type": "number", "default": 1.1, "min": 1.0, "max": 2.0},
        "easing":    {"type": "string", "default": "ease_in_out"},
    },
    description=(
        "Smooth scale-up / scale-down loop that makes the asset breathe. "
        "Works on any opaque or transparent asset."
    ),
)

_GLOW = MotionPreset(
    id="glow",
    name="Glow",
    loopable=True,
    duration_ms=1200,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["letter", "number", "symbol", "signal", "icon"],
    parameter_schema={
        "glow_color":   {"type": "string", "default": "#ffffff"},
        "glow_radius":  {"type": "number", "default": 12, "min": 2, "max": 40},
        "intensity_min":{"type": "number", "default": 0.3, "min": 0.0, "max": 1.0},
        "intensity_max":{"type": "number", "default": 1.0, "min": 0.0, "max": 1.0},
    },
    description=(
        "Animated outer glow that pulses between low and high intensity. "
        "Ideal for neon-themed assets."
    ),
)

_WOBBLE = MotionPreset(
    id="wobble",
    name="Wobble",
    loopable=True,
    duration_ms=600,
    alpha_safe=True,
    overlay_safe=False,
    sticker_safe=True,
    recommended_categories=["letter", "number", "emoji", "icon"],
    parameter_schema={
        "angle_deg": {"type": "number", "default": 8, "min": 1, "max": 30},
        "pivot":     {"type": "string", "default": "center"},
    },
    description=(
        "Left-right rotation oscillation. Best with small icons and emoji."
    ),
)

_BOUNCE = MotionPreset(
    id="bounce",
    name="Bounce",
    loopable=True,
    duration_ms=700,
    alpha_safe=True,
    overlay_safe=False,
    sticker_safe=True,
    recommended_categories=["letter", "number", "emoji", "symbol"],
    parameter_schema={
        "amplitude_px": {"type": "number", "default": 20, "min": 5, "max": 80},
        "squash":       {"type": "boolean", "default": True},
    },
    description=(
        "Vertical bounce with optional squash-and-stretch on landing."
    ),
)

_ORBIT = MotionPreset(
    id="orbit",
    name="Orbit",
    loopable=True,
    duration_ms=2000,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["particle", "symbol", "icon", "frame"],
    parameter_schema={
        "radius_px":   {"type": "number", "default": 30, "min": 10, "max": 120},
        "speed_factor":{"type": "number", "default": 1.0, "min": 0.1, "max": 5.0},
        "clockwise":   {"type": "boolean", "default": True},
    },
    description=(
        "Circular orbit around the asset's centre. "
        "Suitable for particle and decoration elements."
    ),
)

_GLITCH = MotionPreset(
    id="glitch",
    name="Glitch",
    loopable=True,
    duration_ms=500,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["letter", "number", "signal", "icon"],
    parameter_schema={
        "shift_px":      {"type": "number", "default": 6, "min": 1, "max": 20},
        "color_channels":{"type": "array",  "default": ["r", "g", "b"]},
        "frames":        {"type": "number", "default": 8, "min": 4, "max": 20},
    },
    description=(
        "RGB channel shift glitch effect. Great for cyberpunk and signal themes."
    ),
)

_SPARKLE = MotionPreset(
    id="sparkle",
    name="Sparkle",
    loopable=True,
    duration_ms=1500,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["symbol", "emoji", "particle", "icon"],
    parameter_schema={
        "count":        {"type": "number", "default": 8, "min": 2, "max": 20},
        "size_min_px":  {"type": "number", "default": 3, "min": 1, "max": 10},
        "size_max_px":  {"type": "number", "default": 8, "min": 2, "max": 20},
        "color":        {"type": "string", "default": "#ffe066"},
    },
    description=(
        "Twinkling star/sparkle particles orbiting the asset. "
        "Works on any asset category."
    ),
)

_PARTICLE_BURST = MotionPreset(
    id="particle_burst",
    name="Particle Burst",
    loopable=False,
    duration_ms=1000,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=False,
    recommended_categories=["symbol", "emoji", "icon", "particle"],
    parameter_schema={
        "particle_count": {"type": "number", "default": 16, "min": 4, "max": 40},
        "burst_radius_px":{"type": "number", "default": 80, "min": 20, "max": 200},
        "fade_out":       {"type": "boolean", "default": True},
        "color":          {"type": "string", "default": "#ffffff"},
    },
    description=(
        "One-shot radial particle explosion from the centre of the asset. "
        "Not sticker_safe because Telegram stickers require looping animations."
    ),
)

_LASER_SWEEP = MotionPreset(
    id="laser_sweep",
    name="Laser Sweep",
    loopable=True,
    duration_ms=1000,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["signal", "letter", "number", "frame"],
    parameter_schema={
        "color":      {"type": "string", "default": "#00ffff"},
        "width_px":   {"type": "number", "default": 3, "min": 1, "max": 10},
        "direction":  {"type": "string", "default": "horizontal", "enum": ["horizontal", "vertical", "diagonal"]},
    },
    description=(
        "A bright laser line sweeps across the asset — horizontal, vertical, "
        "or diagonal.  Ideal for signal and DJ themes."
    ),
)

_SIGNAL_FLASH = MotionPreset(
    id="signal_flash",
    name="Signal Flash",
    loopable=True,
    duration_ms=400,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["signal", "icon", "letter", "symbol"],
    parameter_schema={
        "on_duration_ms":  {"type": "number", "default": 200, "min": 50, "max": 400},
        "off_duration_ms": {"type": "number", "default": 200, "min": 50, "max": 400},
        "flash_color":     {"type": "string", "default": "#ffffff"},
    },
    description=(
        "Hard on/off strobe flash effect. Useful for signal indicators and alerts."
    ),
)


# ── Catalog dict ──────────────────────────────────────────────

PRESETS: Dict[str, MotionPreset] = {
    p.id: p
    for p in [
        _PULSE,
        _GLOW,
        _WOBBLE,
        _BOUNCE,
        _ORBIT,
        _GLITCH,
        _SPARKLE,
        _PARTICLE_BURST,
        _LASER_SWEEP,
        _SIGNAL_FLASH,
    ]
}


# ── Helpers ───────────────────────────────────────────────────

def get_preset(preset_id: str) -> MotionPreset:
    """
    Return the preset with *preset_id*.

    Raises:
        KeyError: if *preset_id* is not registered.
    """
    if preset_id not in PRESETS:
        raise KeyError(
            f"Unknown motion preset {preset_id!r}. "
            f"Available: {list(PRESETS)}"
        )
    return PRESETS[preset_id]


def list_presets() -> list:
    """Return all registered presets as a list."""
    return list(PRESETS.values())

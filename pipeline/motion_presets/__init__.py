"""Public motion-preset model and canonical registry.

The package-level API uses the documented ``duration``/``notes`` schema.  The
legacy ``pipeline.motion_presets.preset`` and ``catalog`` modules remain
available for older integrations that use ``duration_ms``/``description``.
Keeping the registries separate prevents import order from changing the public
contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MotionPreset:
    """Describe a reusable animation effect in seconds."""

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

    def is_recommended_for(self, category: str) -> bool:
        return not self.recommended_categories or category in self.recommended_categories

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "loopable": self.loopable,
            "duration": self.duration,
            "alpha_safe": self.alpha_safe,
            "overlay_safe": self.overlay_safe,
            "sticker_safe": self.sticker_safe,
            "recommended_categories": list(self.recommended_categories),
            "parameter_schema": dict(self.parameter_schema),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MotionPreset":
        return cls(
            id=data["id"],
            name=data["name"],
            loopable=data.get("loopable", True),
            duration=float(data.get("duration", 2.0)),
            alpha_safe=data.get("alpha_safe", True),
            overlay_safe=data.get("overlay_safe", True),
            sticker_safe=data.get("sticker_safe", True),
            recommended_categories=list(data.get("recommended_categories", [])),
            parameter_schema=dict(data.get("parameter_schema", {})),
            notes=data.get("notes", ""),
        )


_FALLBACK_SPECS = (
    ("pulse", "Pulse", True, 0.8, True, True, True),
    ("glow", "Glow", True, 1.2, True, True, True),
    ("wobble", "Wobble", True, 0.6, True, False, True),
    ("bounce", "Bounce", True, 0.7, True, False, True),
    ("orbit", "Orbit", True, 2.0, True, True, False),
    ("glitch", "Glitch", True, 0.5, False, True, True),
    ("sparkle", "Sparkle", True, 1.5, True, True, True),
    ("particle_burst", "Particle Burst", False, 1.0, True, True, False),
    ("laser_sweep", "Laser Sweep", True, 1.0, True, True, True),
    ("signal_flash", "Signal Flash", True, 0.4, True, True, True),
)

BUILTIN_PRESETS = [
    MotionPreset(
        id=preset_id,
        name=name,
        loopable=loopable,
        duration=duration,
        alpha_safe=alpha_safe,
        overlay_safe=overlay_safe,
        sticker_safe=sticker_safe,
        notes=f"Built-in {name} motion preset.",
    )
    for preset_id, name, loopable, duration, alpha_safe, overlay_safe, sticker_safe in _FALLBACK_SPECS
]
PRESET_REGISTRY = {preset.id: preset for preset in BUILTIN_PRESETS}


def get_preset(preset_id: str) -> MotionPreset | None:
    """Return a canonical preset by ID, or ``None`` when absent."""
    return PRESET_REGISTRY.get(preset_id)


def list_presets(
    *,
    category: str | None = None,
    sticker_safe: bool | None = None,
    overlay_safe: bool | None = None,
) -> list[MotionPreset]:
    """Return canonical presets filtered by category and safety flags."""
    result = list(BUILTIN_PRESETS)
    if category is not None:
        result = [
            preset
            for preset in result
            if not preset.recommended_categories
            or category in preset.recommended_categories
        ]
    if sticker_safe is not None:
        result = [preset for preset in result if preset.sticker_safe is sticker_safe]
    if overlay_safe is not None:
        result = [preset for preset in result if preset.overlay_safe is overlay_safe]
    return result

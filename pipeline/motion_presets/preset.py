"""
pipeline/motion_presets/preset.py – MotionPreset data model.

A MotionPreset describes one reusable animation effect that can be applied to
any compatible base asset.  Presets are intentionally abstract — they carry
parameter schemas and compatibility hints but do not embed rendering code.
Rendering happens in the exporter layer.

This separation allows the same preset to be used by multiple export backends
(e.g. both the GIF exporter and the WebM exporter apply "pulse" using their own
rendering logic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MotionPreset:
    """
    Describes a single, reusable animation effect.

    Attributes:
        id:                     Unique identifier (e.g. ``"pulse"``).
        name:                   Human-readable display name.
        loopable:               Whether the animation loops seamlessly.
        duration_ms:            Approximate animation duration in milliseconds.
        alpha_safe:             True when the preset preserves alpha/transparency.
        overlay_safe:           True when the output is suitable for overlay use.
        sticker_safe:           True when the output satisfies Telegram sticker limits.
        recommended_categories: Asset categories this preset works best with.
                                Empty list means it is compatible with all categories.
        parameter_schema:       JSON-Schema-style dict describing tunable parameters.
                                Rendering backends read these to drive their effects.
        description:            Human-readable description of the visual effect.
    """

    id: str
    name: str
    loopable: bool = True
    duration_ms: int = 1000
    alpha_safe: bool = True
    overlay_safe: bool = True
    sticker_safe: bool = True
    recommended_categories: List[str] = field(default_factory=list)
    parameter_schema: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    # ── Helpers ───────────────────────────────────────────────

    def is_recommended_for(self, category: str) -> bool:
        """Return True if this preset is recommended for *category*."""
        return (
            not self.recommended_categories
            or category in self.recommended_categories
        )

    # ── Serialisation ─────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "loopable": self.loopable,
            "duration_ms": self.duration_ms,
            "alpha_safe": self.alpha_safe,
            "overlay_safe": self.overlay_safe,
            "sticker_safe": self.sticker_safe,
            "recommended_categories": self.recommended_categories,
            "parameter_schema": self.parameter_schema,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MotionPreset":
        return cls(
            id=data["id"],
            name=data["name"],
            loopable=data.get("loopable", True),
            duration_ms=data.get("duration_ms", 1000),
            alpha_safe=data.get("alpha_safe", True),
            overlay_safe=data.get("overlay_safe", True),
            sticker_safe=data.get("sticker_safe", True),
            recommended_categories=data.get("recommended_categories", []),
            parameter_schema=data.get("parameter_schema", {}),
            description=data.get("description", ""),
        )

    def __repr__(self) -> str:
        return (
            f"<MotionPreset id={self.id!r} duration_ms={self.duration_ms} "
            f"loopable={self.loopable}>"
        )

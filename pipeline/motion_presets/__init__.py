"""pipeline/motion_presets – Reusable animation preset system."""

from .preset import MotionPreset
from .catalog import PRESETS, get_preset, list_presets

__all__ = ["MotionPreset", "PRESETS", "get_preset", "list_presets"]

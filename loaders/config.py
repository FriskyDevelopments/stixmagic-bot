"""
loaders/config.py – Configuration for the magical loader system.

Tune these values to adjust animation behaviour globally.
Individual commands can pass a custom LoaderConfig instance to
LoaderController to override settings per-command.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class LoaderConfig:
    # Master switch — set to False to disable animation everywhere.
    loaders_enabled: bool = True

    # How long (ms) an operation must run before animation is shown.
    # Fast operations stay on the initial static caption.
    min_duration_for_animation_ms: int = 2500

    # Pause between frame edits (ms).  900–1200 ms feels premium.
    frame_interval_ms: int = 1000

    # Maximum frames to cycle per loop (capped to actual frame count).
    max_frames_per_loop: int = 3

    # When an edit fails (rate-limit, network), fall back to static
    # instead of retrying and spamming the API.
    fallback_to_static_on_edit_failure: bool = True

    # Emoji used as the "sticker subject" inside frame compositions.
    default_sticker_placeholder: str = "🟣"

    # Default caption pool used when a loader has no dedicated captions.
    default_caption_set: List[str] = field(default_factory=lambda: [
        "✨ summoning sticker...",
        "🌟 applying magic...",
        "⚡ charging effect...",
        "💫 polishing sparkle...",
        "🔮 weaving enchantment...",
        "☁️ shaping dream dust...",
    ])


# Shared default config — import and use this unless you need a custom one.
DEFAULT_CONFIG = LoaderConfig()

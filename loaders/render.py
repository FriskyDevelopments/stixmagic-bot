"""
loaders/render.py – Rendering helpers for loader messages.

Public API:
  render_frame(loader, frame_idx, caption, placeholder)
      → str  (Telegram HTML-safe message text)

  render_static(caption)
      → str  (plain caption with no frame, for static/fast-op mode)
"""

import random

from .config import DEFAULT_CONFIG


def render_frame(
    loader: dict,
    frame_idx: int,
    caption: str | None = None,
    placeholder: str | None = None,
    config=None,
) -> str:
    """
    Compose a caption + frame into a single Telegram message string.

    caption     : override the loader's caption; None picks one randomly.
    placeholder : override the sticker emoji inside the frame composition.
    """
    cfg = config or DEFAULT_CONFIG
    frames = loader["frames"]
    frame = frames[frame_idx % len(frames)]

    # Substitute sticker placeholder if a custom one is requested.
    effective_placeholder = placeholder or cfg.default_sticker_placeholder
    if effective_placeholder != "🟣":
        frame = frame.replace("🟣", effective_placeholder)

    # Pick caption.
    if caption is None:
        caption_pool = loader.get("captions") or cfg.default_caption_set
        caption = random.choice(caption_pool)

    return f"{caption}\n\n{frame}"


def render_static(caption: str) -> str:
    """Return a plain static status message (no frame block)."""
    return caption

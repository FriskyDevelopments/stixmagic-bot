"""
pipeline/exporters/gif_exporter.py – GIF animated sticker exporter.

STATUS: placeholder implementation.

The current implementation writes a stub file to disk so the pipeline
infrastructure can be exercised end-to-end.  Replace the body of
``_render_frames`` with real Pillow frame-composition code once the motion
rendering engine is implemented.

Real implementation notes
-------------------------
- Use ``PIL.Image`` to composite each animation frame.
- Apply the motion preset parameters from ``preset.parameter_schema``.
- Save with ``img.save(..., format='GIF', save_all=True, append_images=...,
  loop=0, duration=frame_ms)``.
- Target file size ≤ 256 KB for Telegram compatibility.
"""

from __future__ import annotations

import logging
import os

from pipeline.asset_model.asset import Asset
from pipeline.motion_presets.preset import MotionPreset
from pipeline.exporters.base import BaseExporter, ExportResult

logger = logging.getLogger(__name__)


class GifExporter(BaseExporter):
    """Export an animated GIF from a base asset + motion preset."""

    format_id = "gif"

    def export(self, asset: Asset, preset: MotionPreset) -> ExportResult:
        """
        Render *asset* with *preset* and write a ``.gif`` file.

        .. note::
            **Placeholder** — writes an empty stub file.
            Replace ``_render_frames`` with real Pillow frame composition.
        """
        path = self.output_path(asset, preset)

        try:
            frames = self._render_frames(asset, preset)
            with open(path, "wb") as fh:
                fh.write(frames)
            logger.info("GifExporter: wrote %s (%d bytes)", path, len(frames))
            return self._result_ok(path)
        except Exception as exc:
            logger.error("GifExporter failed for %s/%s: %s", asset.id, preset.id, exc)
            return self._result_err(str(exc))

    def _render_frames(self, asset: Asset, preset: MotionPreset) -> bytes:
        """
        Compose animation frames and return raw GIF bytes.

        PLACEHOLDER: returns a minimal valid GIF89a header so pipeline
        integration tests can verify file creation without real rendering.
        Replace with Pillow-based frame composition.
        """
        # Minimal GIF89a (1×1 transparent pixel, 1 frame)
        return (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
            b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
            b"\x00\x00\x02\x02D\x01\x00;"
        )

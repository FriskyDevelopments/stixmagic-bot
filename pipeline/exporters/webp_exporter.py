"""
pipeline/exporters/webp_exporter.py – Animated WebP sticker exporter.

STATUS: placeholder implementation.

Real implementation notes
-------------------------
- Use ``PIL.Image`` to composite frames (same frame logic as the GIF exporter).
- Save with ``img.save(..., format='WEBP', save_all=True, append_images=...,
  loop=0, duration=frame_ms)``.
- Pillow ≥ 3.4 supports animated WebP.
- Target file size ≤ 256 KB for Telegram animated sticker compatibility.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pipeline.asset_model.asset import Asset
from pipeline.motion_presets.preset import MotionPreset
from pipeline.exporters.base import BaseExporter, ExportResult

logger = logging.getLogger(__name__)


class AnimatedWebpExporter(BaseExporter):
    """Export an animated WebP from a base asset + motion preset."""

    format_id = "webp"

    def output_path(self, asset: Asset, preset: MotionPreset, suffix: str = "") -> str:
        subdir = Path(self.renders_dir) / self.format_id
        subdir.mkdir(parents=True, exist_ok=True)
        filename = f"{asset.id}_{preset.id}{suffix}.webp"
        return str(subdir / filename)

    def export(self, asset: Asset, preset: MotionPreset) -> ExportResult:
        """
        Render *asset* with *preset* and write an animated ``.webp`` file.

        .. note::
            **Placeholder** — writes a stub RIFF/WEBP header.
            Replace ``_render_frames`` with Pillow animated-WebP composition.
        """
        path = self.output_path(asset, preset)

        try:
            data = self._render_frames(asset, preset)
            with open(path, "wb") as fh:
                fh.write(data)
            logger.info("AnimatedWebpExporter: wrote %s (%d bytes)", path, len(data))
            return ExportResult(format=self.format_id, path=path, success=True, message="OK", size_bytes=len(data))
        except Exception as exc:
            logger.error("AnimatedWebpExporter failed for %s/%s: %s", asset.id, preset.id, exc)
            return ExportResult(format=self.format_id, success=False, message=str(exc))

    def _render_frames(self, asset: Asset, preset: MotionPreset) -> bytes:
        """
        PLACEHOLDER: returns a minimal RIFF/WEBP container header.
        Replace with Pillow animated WebP composition.
        """
        # Minimal RIFF WebP header (not a valid full image; placeholder only)
        payload = b"WEBPVP8 \x00\x00\x00\x00"
        size = len(payload) + 4
        return b"RIFF" + size.to_bytes(4, "little") + payload

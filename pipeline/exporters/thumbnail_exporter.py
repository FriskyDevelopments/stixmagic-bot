"""
pipeline/exporters/thumbnail_exporter.py – Preview thumbnail exporter.

Thumbnails are static JPEG/PNG previews of the first (or most representative)
frame of an animated asset.  They are used in pack listings, the Mini App
catalog, and asset documentation.

STATUS: placeholder implementation.

Real implementation notes
-------------------------
- Open the source asset file (PNG/SVG/WebP) with Pillow.
- Optionally apply the first frame of the motion preset for a more dynamic
  preview.
- Resize to 256×256 (square, centred on transparent canvas).
- Save as JPEG (quality 85) for smallest file size.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pipeline.asset_model.asset import Asset
from pipeline.motion_presets.preset import MotionPreset
from pipeline.exporters.base import BaseExporter, ExportResult

logger = logging.getLogger(__name__)

# Minimal 1×1 JPEG used as placeholder thumbnail
_STUB_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n"
    b"\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d"
    b"\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1edL\xc0\x00"
    b"\x00\x01\x01\x01\x00\x01\x00\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01"
    b"\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04"
    b"\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb"
    b"\xd5\xff\xd9"
)


class ThumbnailExporter(BaseExporter):
    """Export a static JPEG preview thumbnail for an asset + preset pair."""

    format_id = "thumbnails"

    def output_path(self, asset: Asset, preset: MotionPreset, suffix: str = "") -> str:
        subdir = Path(self.renders_dir) / self.format_id
        subdir.mkdir(parents=True, exist_ok=True)
        filename = f"{asset.id}_{preset.id}{suffix}_preview.jpg"
        return str(subdir / filename)

    def export(self, asset: Asset, preset: MotionPreset) -> ExportResult:
        """
        Write a JPEG thumbnail for *asset* + *preset*.

        .. note::
            **Placeholder** — writes a minimal stub JPEG.
            Replace ``_render_thumbnail`` with Pillow-based first-frame render.
        """
        path = self.output_path(asset, preset)

        try:
            data = self._render_thumbnail(asset, preset)
            with open(path, "wb") as fh:
                fh.write(data)
            logger.info("ThumbnailExporter: wrote %s (%d bytes)", path, len(data))
            return ExportResult(format=self.format_id, path=path, success=True, message="OK", size_bytes=len(data))
        except Exception as exc:
            logger.error(
                "ThumbnailExporter failed for %s/%s: %s", asset.id, preset.id, exc
            )
            return ExportResult(format=self.format_id, success=False, message=str(exc))

    def _render_thumbnail(self, asset: Asset, preset: MotionPreset) -> bytes:
        """
        PLACEHOLDER: returns a minimal stub JPEG.
        Replace with Pillow first-frame render at 256×256.
        """
        return _STUB_JPEG

"""
pipeline/exporters/__init__.py – MagicStix multi-format export pipeline.

Each exporter function takes:
  • ``source_path``   – path to a base asset file (PNG/WebP/SVG)
  • ``preset``        – a MotionPreset instance describing the animation
  • ``output_dir``    – directory where the output file should be written
  • (optional kwargs) – format-specific overrides

All functions return the path of the created file on success, or None on
failure.

Current implementation status
------------------------------
export_gif           – PLACEHOLDER  (stub, not yet rendering)
export_animated_webp – PLACEHOLDER  (stub, not yet rendering)
export_webm          – PLACEHOLDER  (stub, not yet rendering)
export_mov           – PLACEHOLDER  (stub, not yet rendering)
export_png_sequence  – PLACEHOLDER  (stub, not yet rendering)
export_thumbnail     – IMPLEMENTED  (saves first-frame/source as PNG thumb)

The ``ExportResult`` dataclass bundles all outputs from a single
``export_all`` run.

Stable interface guarantee
--------------------------
``ExportResult`` is considered a **stable public interface**.  Consumers
should interact with it via the three properties:

* ``sticker_ready_outputs``  – dict of format → path for Telegram stickers
* ``overlay_ready_outputs``  – dict of format → path for overlay compositing
* ``preview_outputs``        – dict of format → path for preview thumbnails

These properties always return a dict (possibly empty).  The individual
nullable attributes (``gif``, ``webp``, ``webm``, ``mov``,
``png_sequence_dir``, ``thumbnail``) are stable too and will never be
removed, though new attributes may be added in future.

Placeholder convention
----------------------
Unimplemented exporters MUST call ``_write_placeholder()`` and log a
``WARNING`` via ``_log_placeholder()`` so operators can clearly identify
which export steps require a real renderer implementation.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from pipeline.motion_presets import MotionPreset

logger = logging.getLogger(__name__)


# ── Output classification ─────────────────────────────────────

STICKER_READY_FORMATS   = {"gif", "webp", "webm"}
OVERLAY_READY_FORMATS   = {"webm", "mov"}
PREVIEW_FORMATS         = {"thumbnail"}


# ── Stable result container ───────────────────────────────────

@dataclass
class ExportResult:
    """
    Bundles every output path produced by a single export_all() call.

    This is a **stable public interface**.  The three properties
    ``sticker_ready_outputs``, ``overlay_ready_outputs``, and
    ``preview_outputs`` are guaranteed to always be present and to
    return a dict (empty when no outputs were produced for that class).

    Attributes
    ----------
    asset_id:
        The source asset's id slug.
    preset_id:
        The motion preset id slug.
    gif:
        Path to the exported GIF file, or None.
    webp:
        Path to the exported animated WebP file, or None.
    webm:
        Path to the exported WebM-with-alpha file, or None.
    mov:
        Path to the exported MOV-with-alpha file, or None.
    png_sequence_dir:
        Directory containing the exported PNG frame sequence, or None.
    thumbnail:
        Path to the preview thumbnail PNG, or None.
    errors:
        List of error messages for any formats that failed.
    """

    asset_id: str
    preset_id: str
    gif:              Optional[str] = None
    webp:             Optional[str] = None
    webm:             Optional[str] = None
    mov:              Optional[str] = None
    png_sequence_dir: Optional[str] = None
    thumbnail:        Optional[str] = None
    errors:           list[str]     = field(default_factory=list)

    @property
    def sticker_ready_outputs(self) -> dict[str, str]:
        """Always-present dict of format → path for Telegram-sticker-ready outputs."""
        result: dict[str, str] = {}
        if self.gif:
            result["gif"] = self.gif
        if self.webp:
            result["webp"] = self.webp
        if self.webm:
            result["webm"] = self.webm
        return result

    @property
    def overlay_ready_outputs(self) -> dict[str, str]:
        """Always-present dict of format → path for overlay-compositor-ready outputs."""
        result: dict[str, str] = {}
        if self.webm:
            result["webm"] = self.webm
        if self.mov:
            result["mov"] = self.mov
        return result

    @property
    def preview_outputs(self) -> dict[str, str]:
        """Always-present dict of format → path for preview / thumbnail outputs."""
        result: dict[str, str] = {}
        if self.thumbnail:
            result["thumbnail"] = self.thumbnail
        return result


# ── Output filename helper ────────────────────────────────────

def _output_name(asset_id: str, preset_id: str, ext: str) -> str:
    """Return a canonical output filename, e.g. ``letter_A_pulse.gif``."""
    return f"{asset_id}_{preset_id}.{ext}"


def _export_placeholder_file(
    exporter_name: str,
    ext: str,
    format_name: str,
    source_path: str,
    preset_id: str,
    output_dir: str,
) -> str | None:
    """Helper to generate a generic placeholder file export."""
    asset_id = source_path_to_id(source_path)
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, _output_name(asset_id, preset_id, ext))
    _write_placeholder(out_path, f"{format_name} placeholder | asset={source_path} | preset={preset_id}")
    _log_placeholder(exporter_name, out_path)
    return out_path


# ── Individual format exporters ───────────────────────────────

def export_gif(
    source_path: str,
    preset: MotionPreset,
    output_dir: str,
    **kwargs,
) -> str | None:
    """
    Export an animated GIF for the given source and preset.
    
    This is a placeholder exporter: it writes a small marker file at the canonical output path so downstream steps can reference the expected GIF location.
    
    Returns:
        out_path (str | None): Path to the created placeholder GIF file, or `None` if the export failed.
    """
    return _export_placeholder_file("export_gif", "gif", "GIF", source_path, preset.id, output_dir)


def export_animated_webp(
    source_path: str,
    preset: MotionPreset,
    output_dir: str,
    **kwargs,
) -> str | None:
    """
    Export an animated WebP for the given source using the provided preset.
    
    This is a placeholder exporter: it writes a small text placeholder file named "{asset_id}_{preset_id}.webp" into output_dir and does not perform real frame rendering.
    
    Returns:
        str | None: Path to the created placeholder `.webp` file, or `None` if the export failed.
    """
    return _export_placeholder_file("export_animated_webp", "webp", "WEBP", source_path, preset.id, output_dir)


def export_webm(
    source_path: str,
    preset: MotionPreset,
    output_dir: str,
    **kwargs,
) -> str | None:
    """
    Produce a WebM export file for the given source asset and preset (placeholder implementation).
    
    This function writes a small UTF-8 placeholder file named "{asset_id}_{preset_id}.webm" into the specified output directory and logs a warning that the exporter is a placeholder.
    
    Returns:
        out_path (str): Path to the created placeholder WebM file, or `None` if the export failed.
    """
    return _export_placeholder_file("export_webm", "webm", "WEBM", source_path, preset.id, output_dir)


def export_mov(
    source_path: str,
    preset: MotionPreset,
    output_dir: str,
    **kwargs,
) -> str | None:
    """
    Write a placeholder MOV export file for the given source and preset and return its path.
    
    This is a stub that writes a text placeholder at the canonical output filename (no real encoding is performed).
    
    Returns:
        out_path (str | None): Filesystem path to the created placeholder MOV file, or `None` if creation failed.
    """
    return _export_placeholder_file("export_mov", "mov", "MOV", source_path, preset.id, output_dir)


def export_png_sequence(
    source_path: str,
    preset: MotionPreset,
    output_dir: str,
    *,
    fps: int = 30,
    **kwargs,
) -> str | None:
    """
    Prepare a numbered PNG frame sequence directory for the given source and preset.
    
    This creates (if needed) a directory named "{asset_id}_{preset.id}_frames" inside output_dir, writes a placeholder frame file into that directory, and returns the directory path. Real frame rendering is not implemented; the function currently writes a textual placeholder to indicate where frames would be produced.
    
    Parameters:
    	source_path (str): Path to the source asset; used to derive the asset id.
    	preset (MotionPreset): Preset that determines naming; only its `id` is used.
    	output_dir (str): Root directory where the frames directory will be created.
    	fps (int): Frames per second that would be used for the sequence.
    
    Returns:
    	seq_dir (str | None): Path to the created frames directory, or `None` on failure.
    """
    asset_id = source_path_to_id(source_path)
    seq_dir = os.path.join(output_dir, f"{asset_id}_{preset.id}_frames")
    os.makedirs(seq_dir, exist_ok=True)
    placeholder_file = os.path.join(seq_dir, "frame_0000.txt")
    _write_placeholder(
        placeholder_file,
        f"PNG sequence placeholder | asset={source_path} | preset={preset.id} | fps={fps}",
    )
    _log_placeholder("export_png_sequence", seq_dir)
    return seq_dir


def export_thumbnail(
    source_path: str,
    output_dir: str,
    *,
    size: tuple[int, int] = (256, 256),
    **kwargs,
) -> str | None:
    """
    Copy / resize the source asset as a preview thumbnail PNG.

    This is the only *implemented* exporter – it uses Pillow to produce
    a real thumbnail image.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.error("Pillow is required for export_thumbnail")
        return None

    os.makedirs(output_dir, exist_ok=True)
    asset_id = source_path_to_id(source_path)
    out_path = os.path.join(output_dir, f"{asset_id}_thumb.png")

    try:
        img = Image.open(source_path)
        img.thumbnail(size, Image.LANCZOS)
        img.save(out_path, format="PNG")
        logger.info("export_thumbnail: saved %s", out_path)
        return out_path
    except Exception as exc:
        logger.error("export_thumbnail failed for %s: %s", source_path, exc)
        return None


# ── Aggregate exporter ────────────────────────────────────────

def export_all(
    asset_id: str,
    source_path: str,
    preset: MotionPreset,
    *,
    renders_root: str = "renders",
    formats: list[str] | None = None,
) -> ExportResult:
    """
    Run all (or a selected subset of) exporters for one asset + preset pair.

    Parameters
    ----------
    asset_id:
        The asset's id slug (used for output filenames and directory layout).
    source_path:
        Absolute or relative path to the source asset file.
    preset:
        The MotionPreset to apply.
    renders_root:
        Root directory for all render outputs (default: ``"renders"``).
    formats:
        List of format strings to export.  Defaults to all formats.
        Supported values: ``"gif"``, ``"webp"``, ``"webm"``, ``"mov"``,
        ``"png_sequence"``, ``"thumbnail"``.

    Returns
    -------
    ExportResult
        Container with paths to every produced output file.
    """
    if formats is None:
        formats = ["gif", "webp", "webm", "mov", "png_sequence", "thumbnail"]

    result = ExportResult(asset_id=asset_id, preset_id=preset.id)

    _dispatch = {
        "gif":          (export_gif,          os.path.join(renders_root, "gif")),
        "webp":         (export_animated_webp, os.path.join(renders_root, "webp")),
        "webm":         (export_webm,          os.path.join(renders_root, "webm")),
        "mov":          (export_mov,           os.path.join(renders_root, "mov")),
        "png_sequence": (export_png_sequence,  os.path.join(renders_root, "png_sequences")),
    }

    for fmt in formats:
        if fmt == "thumbnail":
            path = export_thumbnail(source_path, os.path.join(renders_root, "thumbnails"))
            if path:
                result.thumbnail = path
            else:
                result.errors.append("thumbnail export failed")
            continue

        if fmt not in _dispatch:
            result.errors.append(f"unknown format: {fmt!r}")
            continue

        exporter_fn, out_dir = _dispatch[fmt]
        try:
            path = exporter_fn(source_path, preset, out_dir)
        except Exception as exc:
            result.errors.append(f"{fmt} export raised: {exc}")
            path = None

        if path:
            if fmt == "png_sequence":
                result.png_sequence_dir = path
            else:
                setattr(result, fmt, path)
        else:
            result.errors.append(f"{fmt} export returned None")

    return result


# ── Internal helpers ──────────────────────────────────────────

def source_path_to_id(source_path: str) -> str:
    """Derive a simple asset id slug from a source file path."""
    base = os.path.basename(source_path)
    name, _ = os.path.splitext(base)
    return name


def _write_placeholder(path: str, content: str) -> None:
    """Write a plain-text placeholder file (used by unimplemented exporters)."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"[PLACEHOLDER]\n{content}\n")


def _log_placeholder(exporter_name: str, out_path: str) -> None:
    """
    Emit a standardised WARNING so incomplete exporters are obvious in logs.

    All placeholder exporters MUST call this function so operators can
    grep for ``PLACEHOLDER EXPORTER`` to find every unimplemented step.
    """
    logger.warning(
        "PLACEHOLDER EXPORTER | %s | output=%s | "
        "replace this stub with a real renderer implementation",
        exporter_name,
        out_path,
    )


# ── Class-based exporter backends ────────────────────────────
# base.py and the format-specific exporter files provide OOP wrappers
# around the functional API above.  Imported lazily so this module
# remains loadable even if individual backends are absent.
try:
    from .base import BaseExporter  # noqa: F401
    from .gif_exporter import GifExporter  # noqa: F401
    from .webp_exporter import AnimatedWebpExporter  # noqa: F401
    from .webm_exporter import WebmExporter  # noqa: F401
    from .mov_exporter import MovExporter  # noqa: F401
    from .png_sequence_exporter import PngSequenceExporter  # noqa: F401
    from .thumbnail_exporter import ThumbnailExporter  # noqa: F401
except ImportError:
    pass

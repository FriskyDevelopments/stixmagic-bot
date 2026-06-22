"""
pipeline_adapter.py – Optional bot-to-pipeline integration boundary.

This module provides a thin adapter layer that the Telegram bot (main.py)
can *optionally* call after generating a base asset.  It bridges the bot
layer and the pipeline layer without creating a hard dependency between them.

Design notes
------------
* The bot never imports from ``pipeline/`` directly.  All pipeline calls go
  through this adapter.
* Every function in this module is safe to call even when the asset catalog
  has not been populated — it will log a warning and return gracefully.
* The adapter is completely optional; the bot continues to work unchanged if
  this module is never imported.

Usage (from main.py or a bot command handler)
---------------------------------------------
>>> from pipeline_adapter import register_asset, generate_exports
>>>
>>> # After the bot creates a sticker, optionally register it in the pipeline:
>>> asset_path = "assets/source/stickers/my_sticker.webp"
>>> register_asset(
...     asset_id="sticker_xyz",
...     name="My Sticker",
...     category="sticker",
...     source_path=asset_path,
... )
>>>
>>> # Optionally kick off a pipeline export run:
>>> result = generate_exports("sticker_xyz", asset_path, preset_id="pulse")
>>> if result:
...     print(result.sticker_ready_outputs)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy imports to avoid hard coupling ──────────────────────
# These are imported inside functions so that the adapter module can be
# imported even if the pipeline package is not on sys.path (graceful degrade).


def _load_pipeline():
    """Return (AssetCatalog, Asset, AssetCategory, SourceFormat) or None on failure."""
    try:
        from pipeline.metadata import AssetCatalog
        from pipeline.asset_model import Asset, AssetCategory, SourceFormat
        return AssetCatalog, Asset, AssetCategory, SourceFormat
    except ImportError as exc:
        logger.warning("pipeline_adapter: pipeline package not available – %s", exc)
        return None


# ── Public interface ──────────────────────────────────────────


def register_asset(
    asset_id: str,
    name: str,
    category: str,
    source_path: str,
    *,
    source_format: str | None = None,
    theme: str | None = None,
    tags: list[str] | None = None,
    notes: str = "",
) -> bool:
    """
    Register a bot-generated asset in the pipeline asset catalog.

    Adds or overwrites the asset record in ``assets/catalog.json`` so the
    pipeline can later export it into multiple formats.

    Parameters
    ----------
    asset_id:
        Unique slug for the asset (e.g. ``"sticker_xyz"``).
    name:
        Human-readable label.
    category:
        Asset category string (e.g. ``"sticker"``, ``"letter"``).
        Must match one of the :class:`~pipeline.asset_model.AssetCategory` values.
    source_path:
        Path to the base asset file relative to the repository root.
    source_format:
        File format string (``"png"``, ``"webp"``, etc.).
        Inferred from *source_path* extension when omitted.
    theme:
        Optional theme string (e.g. ``"neon"``).
    tags:
        Optional list of keyword tags.
    notes:
        Optional free-form remarks.

    Returns
    -------
    bool
        True on success, False if the pipeline package is unavailable or the
        category / format value is unrecognised.
    """
    modules = _load_pipeline()
    if modules is None:
        return False

    AssetCatalog, Asset, AssetCategory, SourceFormat = modules

    # Infer source format from file extension when not supplied
    if source_format is None:
        ext = os.path.splitext(source_path)[1].lstrip(".").lower()
        source_format = ext or "png"

    try:
        cat  = AssetCategory(category)
        fmt  = SourceFormat(source_format)
    except ValueError as exc:
        logger.error("pipeline_adapter.register_asset: invalid value – %s", exc)
        return False

    from pipeline.asset_model import AssetTheme
    resolved_theme = None
    if theme:
        try:
            resolved_theme = AssetTheme(theme)
        except ValueError:
            logger.warning("pipeline_adapter.register_asset: unknown theme %r – ignoring", theme)

    asset = Asset(
        id=asset_id,
        name=name,
        category=cat,
        source_format=fmt,
        source_path=source_path,
        theme=resolved_theme,
        tags=tags or [],
        notes=notes,
    )

    catalog = AssetCatalog(auto_load=True)
    catalog.add(asset)
    catalog.save()
    logger.info("pipeline_adapter: registered asset %r in catalog", asset_id)
    return True



def _load_export_modules():
    try:
        from pipeline.motion_presets import get_preset
        from pipeline.exporters import export_all
        return get_preset, export_all
    except ImportError as exc:
        logger.warning("pipeline_adapter: pipeline package not available – %s", exc)
        return None

def _get_preset_for_export(get_preset_fn, preset_id: str):
    preset = get_preset_fn(preset_id)
    if preset is None:
        logger.error(
            "pipeline_adapter.generate_exports: preset %r not found – skipping export",
            preset_id,
        )
        return None
    return preset

def generate_exports(
    asset_id: str,
    source_path: str,
    preset_id: str = "pulse",
    *,
    renders_root: str = "renders",
    formats: list[str] | None = None,
) -> Any | None:
    """
    Run the export pipeline for a single asset + preset combination.

    This is the main entry point for the bot to trigger multi-format exports.
    It is a thin wrapper around :func:`pipeline.exporters.export_all`.

    Parameters
    ----------
    asset_id:
        The asset's id slug.
    source_path:
        Path to the base asset file.
    preset_id:
        Motion preset to apply (default: ``"pulse"``).
    renders_root:
        Root directory for export outputs (default: ``"renders"``).
    formats:
        List of format strings.  ``None`` = all formats.

    Returns
    -------
    ExportResult or None
        The export result container, or None if the pipeline is unavailable
        or the preset is not found.
    """
    modules = _load_export_modules()
    if modules is None:
        return None
    get_preset, export_all = modules

    preset = _get_preset_for_export(get_preset, preset_id)
    if preset is None:
        return None

    logger.info(
        "pipeline_adapter: running export for asset=%r preset=%r formats=%r",
        asset_id, preset_id, formats,
    )
    return export_all(
        asset_id,
        source_path,
        preset,
        renders_root=renders_root,
        formats=formats,
    )


def get_export_status(asset_id: str, preset_id: str, renders_root: str = "renders") -> dict[str, bool]:
    """
    Check which export formats already exist on disk for an asset+preset pair.

    Returns a dict mapping format name → True/False (file exists).

    Parameters
    ----------
    asset_id:
        The asset's id slug.
    preset_id:
        The motion preset id slug.
    renders_root:
        Root directory of export outputs.
    """
    try:
        from pipeline.exporters import _output_name
    except ImportError:
        _output_name = lambda a, p, e: f"{a}_{p}.{e}"  # noqa: E731

    _format_paths = {
        "gif":       os.path.join(renders_root, "gif",        _output_name(asset_id, preset_id, "gif")),
        "webp":      os.path.join(renders_root, "webp",       _output_name(asset_id, preset_id, "webp")),
        "webm":      os.path.join(renders_root, "webm",       _output_name(asset_id, preset_id, "webm")),
        "mov":       os.path.join(renders_root, "mov",        _output_name(asset_id, preset_id, "mov")),
        "thumbnail": os.path.join(renders_root, "thumbnails", f"{asset_id}_thumb.png"),
    }
    return {fmt: os.path.exists(path) for fmt, path in _format_paths.items()}

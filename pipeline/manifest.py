"""
pipeline/manifest.py – MagicStix pipeline manifest generator.

Generates a ``pipeline_manifest.json`` file that summarises every pack,
its included assets, their preview thumbnails, and the expected export
paths.  This manifest is designed to be consumed by:

* The MagicStix web repository / API
* Browser extension asset loaders
* Overlay compositor asset discovery
* Any future tooling that needs a machine-readable index of all rendered
  outputs without walking the directory tree.

Usage
-----
>>> from pipeline.manifest import generate_pipeline_manifest
>>> manifest = generate_pipeline_manifest(output_path="pipeline_manifest.json")

Or from the command line::

    python -m pipeline.manifest

Schema
------
The generated JSON has the following top-level structure::

    {
      "generated_at": "ISO-8601 timestamp",
      "total_packs": <int>,
      "total_assets": <int>,
      "packs": [
        {
          "pack_id": "motion_alphabet",
          "title": "MagicStix Motion Alphabet",
          "theme": "neon",
          "target_platforms": [...],
          "export_formats": [...],
          "entries": [
            {
              "asset_id": "letter_A",
              "asset_name": "Letter A",
              "asset_category": "letter",
              "preset_id": "pulse",
              "thumbnail": "renders/thumbnails/letter_A_thumb.png",
              "outputs": {
                "gif":  "renders/gif/letter_A_pulse.gif",
                "webp": "renders/webp/letter_A_pulse.webp",
                "webm": "renders/webm/letter_A_pulse.webm"
              }
            },
            ...
          ]
        },
        ...
      ]
    }
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = "pipeline_manifest.json"
DEFAULT_PACKS_DIR = "packs"
DEFAULT_RENDERS_ROOT = "renders"


def generate_pipeline_manifest(
    *,
    output_path: str = DEFAULT_MANIFEST_PATH,
    packs_dir: str = DEFAULT_PACKS_DIR,
    renders_root: str = DEFAULT_RENDERS_ROOT,
    catalog_path: str | None = None,
) -> dict[str, Any]:
    """
    Build and write a ``pipeline_manifest.json`` for all defined packs.

    Discovers all ``pack.json`` files under *packs_dir*, loads the asset
    catalog, and calls :func:`~pipeline.packager.build_pack` for each pack
    to produce the manifest.

    Parameters
    ----------
    output_path:
        Path where the manifest JSON will be written
        (default: ``"pipeline_manifest.json"`` in the working directory).
    packs_dir:
        Directory containing per-pack subdirectories with ``pack.json`` files.
    renders_root:
        Root directory of the export outputs tree (for output path resolution).
    catalog_path:
        Override the default asset catalog path.  ``None`` uses the built-in
        default (``assets/catalog.json``).

    Returns
    -------
    dict
        The full manifest as a Python dict (also written to *output_path*).
    """
    from pipeline.metadata import AssetCatalog
    from pipeline.packager import PackDefinition, build_pack

    # Load asset catalog
    catalog_kwargs: dict[str, Any] = {"auto_load": True}
    if catalog_path is not None:
        catalog_kwargs["path"] = catalog_path
    catalog = AssetCatalog(**catalog_kwargs)

    # Discover pack definitions
    pack_json_files: list[str] = []
    if os.path.isdir(packs_dir):
        # ⚡ Bolt Optimization: Use os.scandir() instead of os.listdir()
        # Impact: Improves directory iteration performance, especially on large directories, and avoids redundant stat() calls.
        entries = sorted((e.name for e in os.scandir(packs_dir) if e.is_dir()))
        for entry_name in entries:
            candidate = os.path.join(packs_dir, entry_name, "pack.json")
            if os.path.isfile(candidate):
                pack_json_files.append(candidate)

    if not pack_json_files:
        logger.warning(
            "generate_pipeline_manifest: no pack.json files found under %r", packs_dir
        )

    manifest_packs: list[dict[str, Any]] = []
    total_assets_seen: set[str] = set()

    for pack_file in pack_json_files:
        try:
            pack = PackDefinition.from_file(pack_file)
        except Exception as exc:
            logger.error("Skipping %s – failed to load: %s", pack_file, exc)
            continue

        try:
            pack_manifest = build_pack(
                pack, catalog, renders_root=renders_root, strict_validation=False
            )
        except Exception as exc:
            logger.error("Skipping pack %r – build_pack failed: %s", pack.pack_id, exc)
            continue

        entries: list[dict[str, Any]] = []
        for entry in pack_manifest.entries:
            total_assets_seen.add(entry.asset_id)
            asset = catalog.get(entry.asset_id)
            entries.append({
                "asset_id":       entry.asset_id,
                "asset_name":     asset.name if asset else entry.asset_id,
                "asset_category": asset.category.value if asset else "",
                "preset_id":      entry.preset_id,
                "thumbnail":      entry.expected_outputs.get("thumbnail"),
                "outputs": {
                    fmt: path
                    for fmt, path in entry.expected_outputs.items()
                    if fmt != "thumbnail"
                },
            })

        manifest_packs.append({
            "pack_id":         pack.pack_id,
            "title":           pack.title,
            "theme":           pack.theme,
            "target_platforms": pack.target_platforms,
            "export_formats":  pack.export_formats,
            "entries":         entries,
        })
        logger.info("generate_pipeline_manifest: added pack %r (%d entries)", pack.pack_id, len(entries))

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_packs":  len(manifest_packs),
        "total_assets": len(total_assets_seen),
        "packs":        manifest_packs,
    }

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
        logger.info(
            "generate_pipeline_manifest: wrote %d packs / %d unique assets to %s",
            len(manifest_packs), len(total_assets_seen), output_path,
        )
    except Exception as exc:
        logger.error("Failed to write manifest to %s: %s", output_path, exc)

    return manifest


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MANIFEST_PATH
    result = generate_pipeline_manifest(output_path=out)
    print(
        f"Generated pipeline_manifest.json — "
        f"{result['total_packs']} packs, {result['total_assets']} unique assets"
    )

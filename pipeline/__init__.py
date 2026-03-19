"""
pipeline/ – MagicStix visual asset pipeline.

This package provides a multi-layer system that transforms base assets
(produced by the StixMagic bot) into multiple export formats via reusable
motion presets, and groups those outputs into distributable packs.

Sub-packages
------------
asset_model   – Asset and AssetCatalog data models / schema validation
metadata      – On-disk asset index (JSON catalog persistence)
motion_presets– Reusable animation preset definitions
exporters     – Per-format export drivers (GIF, WebP, WebM, MOV, PNG seq, thumb)
packager      – Pack metadata and automated pack-assembly helpers
"""

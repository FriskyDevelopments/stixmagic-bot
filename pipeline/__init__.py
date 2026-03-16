"""
pipeline – MagicStix visual asset pipeline.

This package provides the five-layer architecture that transforms raw base assets
(letters, symbols, emojis, …) into multi-format animated outputs:

  asset_model   – Core data models (Asset, AssetCategory, AssetTheme)
  metadata      – Asset registry backed by JSON files
  motion_presets– Reusable animation preset definitions
  exporters     – Format-specific render backends (GIF, WebP, WebM, MOV, PNG)
  packager      – Metadata-driven product pack generation

Usage example::

    from pipeline.metadata.registry import AssetRegistry
    from pipeline.motion_presets.catalog import PRESETS
    from pipeline.packager.generator import PackGenerator

    registry = AssetRegistry()
    assets = registry.get_by_category("letter")
    pulse = PRESETS["pulse"]

    generator = PackGenerator(registry)
    generator.generate("motion_alphabet")
"""

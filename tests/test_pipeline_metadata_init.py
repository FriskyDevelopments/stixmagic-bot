import unittest
import tempfile

from pipeline.metadata import AssetCatalog
from pipeline.asset_model.asset import Asset, CATEGORY_LETTER, THEME_NEON, FORMAT_PNG

class TestAssetCatalog(unittest.TestCase):
    def setUp(self):
        # We don't need a real file for these tests, just the in-memory catalog
        self.catalog = AssetCatalog(path="dummy_path.json", auto_load=False)

    def test_by_preset_empty_catalog(self):
        """Test by_preset with an empty catalog returns an empty list."""
        self.assertEqual(self.catalog.by_preset("preset1"), [])

    def test_by_preset_mismatch(self):
        """Test by_preset with a catalog where no assets match the preset."""
        asset1 = Asset(
            id="asset1",
            name="Asset 1",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="dummy.png",
            width=100,
            height=100,
            transparent_background=True,
            animation_compatible_presets=["preset1", "preset2"],
            export_targets=[],
        )
        self.catalog.add(asset1)

        # preset3 is not in animation_compatible_presets
        self.assertEqual(self.catalog.by_preset("preset3"), [])

    def test_by_preset_match(self):
        """Test by_preset with a catalog where an asset matches the preset."""
        asset1 = Asset(
            id="asset1",
            name="Asset 1",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="dummy.png",
            width=100,
            height=100,
            transparent_background=True,
            animation_compatible_presets=["preset1", "preset2"],
            export_targets=[],
        )
        self.catalog.add(asset1)

        # preset1 is in animation_compatible_presets
        self.assertEqual(self.catalog.by_preset("preset1"), [asset1])

    def test_by_preset_empty_compatible_presets(self):
        """Test by_preset when an asset has empty animation_compatible_presets (compatible with all)."""
        asset1 = Asset(
            id="asset1",
            name="Asset 1",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="dummy.png",
            width=100,
            height=100,
            transparent_background=True,
            animation_compatible_presets=[], # empty list means compatible with all
            export_targets=[],
        )
        self.catalog.add(asset1)

        # should match any preset
        self.assertEqual(self.catalog.by_preset("any_preset"), [asset1])

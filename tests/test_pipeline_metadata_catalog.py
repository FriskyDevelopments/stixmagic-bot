import unittest
from pipeline.metadata import AssetCatalog
from pipeline.asset_model.asset import Asset, CATEGORY_LETTER, THEME_NEON, FORMAT_PNG

class TestAssetCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = AssetCatalog(auto_load=False)
        self.asset1 = Asset(
            id="letter_a",
            name="Letter A",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="letter_a.png",
            width=100, height=100,
            animation_compatible_presets=["pulse", "fade"]
        )
        self.catalog.add(self.asset1)

    def test_by_preset_empty_catalog(self):
        empty_catalog = AssetCatalog(auto_load=False)
        self.assertEqual(empty_catalog.by_preset("pulse"), [])

    def test_by_preset_mismatch(self):
        # The catalog has asset1 with "pulse" and "fade" presets.
        # "zoom" is a mismatch.
        res = self.catalog.by_preset("zoom")
        self.assertEqual(res, [])

if __name__ == '__main__':
    unittest.main()

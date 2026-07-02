import unittest
from pipeline.asset_model.asset import Asset, CATEGORY_LETTER, THEME_NEON, FORMAT_PNG, EXPORT_GIF, EXPORT_WEBM

class TestAsset(unittest.TestCase):
    def setUp(self):
        self.base_asset_data = {
            "id": "test_asset",
            "name": "Test Asset",
            "category": CATEGORY_LETTER,
            "theme": THEME_NEON,
            "source_format": FORMAT_PNG,
            "source_path": "path/to/source",
            "width": 100,
            "height": 100,
        }

    def test_supports_export_empty_list(self):
        asset = Asset(**self.base_asset_data)
        self.assertTrue(asset.supports_export(EXPORT_GIF))
        self.assertTrue(asset.supports_export(EXPORT_WEBM))
        self.assertTrue(asset.supports_export("any_other_target"))

    def test_supports_export_specific_targets(self):
        asset = Asset(
            **self.base_asset_data,
            export_targets=[EXPORT_GIF]
        )
        self.assertTrue(asset.supports_export(EXPORT_GIF))
        self.assertFalse(asset.supports_export(EXPORT_WEBM))
        self.assertFalse(asset.supports_export("any_other_target"))

if __name__ == '__main__':
    unittest.main()

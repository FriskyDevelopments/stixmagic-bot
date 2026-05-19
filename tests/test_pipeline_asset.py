import unittest
from pipeline.asset_model.asset import Asset, CATEGORY_LETTER, THEME_NEON, FORMAT_PNG, EXPORT_GIF, EXPORT_PNG_SEQUENCE

class TestAsset(unittest.TestCase):

    def setUp(self):
        self.base_asset_data = {
            "id": "test_asset",
            "name": "Test Asset",
            "category": CATEGORY_LETTER,
            "theme": THEME_NEON,
            "source_format": FORMAT_PNG,
            "source_path": "path/to/source.png",
            "width": 100,
            "height": 100,
            "transparent_background": True,
            "tags": ["test", "tag"],
            "animation_compatible_presets": [],
            "export_targets": [],
            "notes": "Test notes",
        }
        self.asset = Asset.from_dict(self.base_asset_data)

    def test_from_dict_and_to_dict(self):
        asset = Asset.from_dict(self.base_asset_data)
        self.assertEqual(asset.id, "test_asset")
        self.assertEqual(asset.name, "Test Asset")
        self.assertEqual(asset.width, 100)

        # Test serialization back to dict
        serialized = asset.to_dict()
        self.assertEqual(serialized, self.base_asset_data)

    def test_from_dict_defaults(self):
        # Missing optional fields
        minimal_data = {
            "id": "minimal",
            "name": "Minimal",
            "category": CATEGORY_LETTER,
            "theme": THEME_NEON,
            "source_format": FORMAT_PNG,
            "source_path": "minimal.png",
            "width": 50,
            "height": 50,
        }
        asset = Asset.from_dict(minimal_data)
        self.assertEqual(asset.id, "minimal")
        self.assertTrue(asset.transparent_background)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")

    def test_is_animation_compatible(self):
        # Empty list means all compatible
        self.asset.animation_compatible_presets = []
        self.assertTrue(self.asset.is_animation_compatible("any_preset"))

        # Explicit list
        self.asset.animation_compatible_presets = ["preset1", "preset2"]
        self.assertTrue(self.asset.is_animation_compatible("preset1"))
        self.assertTrue(self.asset.is_animation_compatible("preset2"))
        self.assertFalse(self.asset.is_animation_compatible("preset3"))

    def test_supports_export(self):
        # Empty list means all enabled
        self.asset.export_targets = []
        self.assertTrue(self.asset.supports_export(EXPORT_GIF))
        self.assertTrue(self.asset.supports_export(EXPORT_PNG_SEQUENCE))

        # Explicit list
        self.asset.export_targets = [EXPORT_GIF]
        self.assertTrue(self.asset.supports_export(EXPORT_GIF))
        self.assertFalse(self.asset.supports_export(EXPORT_PNG_SEQUENCE))

    def test_repr(self):
        expected_repr = "<Asset id='test_asset' category='letter' theme='neon'>"
        self.assertEqual(repr(self.asset), expected_repr)

if __name__ == '__main__':
    unittest.main()

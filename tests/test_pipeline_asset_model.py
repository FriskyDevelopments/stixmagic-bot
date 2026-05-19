import unittest
from pipeline.asset_model import Asset, AssetCategory, AssetTheme, SourceFormat

class TestAsset(unittest.TestCase):
    def test_default_initialization(self):
        asset = Asset(
            id="test_id",
            name="Test Asset",
            category=AssetCategory.STICKER,
            source_format=SourceFormat.PNG,
            source_path="assets/source/test.png"
        )
        self.assertEqual(asset.id, "test_id")
        self.assertEqual(asset.name, "Test Asset")
        self.assertEqual(asset.category, AssetCategory.STICKER)
        self.assertEqual(asset.source_format, SourceFormat.PNG)
        self.assertEqual(asset.source_path, "assets/source/test.png")
        self.assertEqual(asset.width, 512)
        self.assertEqual(asset.height, 512)
        self.assertTrue(asset.transparent_background)
        self.assertIsNone(asset.theme)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")

    def test_to_dict_minimal(self):
        asset = Asset(
            id="test_id",
            name="Test Asset",
            category=AssetCategory.STICKER,
            source_format=SourceFormat.PNG,
            source_path="assets/source/test.png"
        )
        data = asset.to_dict()
        expected = {
            "id": "test_id",
            "name": "Test Asset",
            "category": "sticker",
            "source_format": "png",
            "source_path": "assets/source/test.png",
            "width": 512,
            "height": 512,
            "transparent_background": True,
            "theme": None,
            "tags": [],
            "animation_compatible_presets": [],
            "export_targets": [],
            "notes": "",
        }
        self.assertEqual(data, expected)

    def test_to_dict_full(self):
        asset = Asset(
            id="test_id",
            name="Test Asset",
            category=AssetCategory.STICKER,
            source_format=SourceFormat.PNG,
            source_path="assets/source/test.png",
            width=1024,
            height=768,
            transparent_background=False,
            theme=AssetTheme.NEON,
            tags=["tag1", "tag2"],
            animation_compatible_presets=["preset1"],
            export_targets=["png", "webp"],
            notes="Some notes"
        )
        data = asset.to_dict()
        expected = {
            "id": "test_id",
            "name": "Test Asset",
            "category": "sticker",
            "source_format": "png",
            "source_path": "assets/source/test.png",
            "width": 1024,
            "height": 768,
            "transparent_background": False,
            "theme": "neon",
            "tags": ["tag1", "tag2"],
            "animation_compatible_presets": ["preset1"],
            "export_targets": ["png", "webp"],
            "notes": "Some notes",
        }
        self.assertEqual(data, expected)

    def test_from_dict_minimal(self):
        data = {
            "id": "test_id",
            "name": "Test Asset",
            "category": "sticker",
            "source_format": "png",
            "source_path": "assets/source/test.png",
        }
        asset = Asset.from_dict(data)
        self.assertEqual(asset.id, "test_id")
        self.assertEqual(asset.name, "Test Asset")
        self.assertEqual(asset.category, AssetCategory.STICKER)
        self.assertEqual(asset.source_format, SourceFormat.PNG)
        self.assertEqual(asset.source_path, "assets/source/test.png")
        self.assertEqual(asset.width, 512)
        self.assertEqual(asset.height, 512)
        self.assertTrue(asset.transparent_background)
        self.assertIsNone(asset.theme)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")

    def test_from_dict_full(self):
        data = {
            "id": "test_id",
            "name": "Test Asset",
            "category": "sticker",
            "source_format": "png",
            "source_path": "assets/source/test.png",
            "width": 1024,
            "height": 768,
            "transparent_background": False,
            "theme": "neon",
            "tags": ["tag1", "tag2"],
            "animation_compatible_presets": ["preset1"],
            "export_targets": ["png", "webp"],
            "notes": "Some notes",
        }
        asset = Asset.from_dict(data)
        self.assertEqual(asset.id, "test_id")
        self.assertEqual(asset.name, "Test Asset")
        self.assertEqual(asset.category, AssetCategory.STICKER)
        self.assertEqual(asset.source_format, SourceFormat.PNG)
        self.assertEqual(asset.source_path, "assets/source/test.png")
        self.assertEqual(asset.width, 1024)
        self.assertEqual(asset.height, 768)
        self.assertFalse(asset.transparent_background)
        self.assertEqual(asset.theme, AssetTheme.NEON)
        self.assertEqual(asset.tags, ["tag1", "tag2"])
        self.assertEqual(asset.animation_compatible_presets, ["preset1"])
        self.assertEqual(asset.export_targets, ["png", "webp"])
        self.assertEqual(asset.notes, "Some notes")

if __name__ == '__main__':
    unittest.main()

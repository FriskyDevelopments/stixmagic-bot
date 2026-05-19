import unittest
from pipeline.asset_model import Asset, AssetCategory, SourceFormat, AssetTheme

class TestAssetModel(unittest.TestCase):
    def test_asset_defaults(self):
        asset = Asset(
            id="test_id",
            name="Test Name",
            category=AssetCategory.LETTER,
            source_format=SourceFormat.PNG,
            source_path="path/to/source.png"
        )
        self.assertEqual(asset.id, "test_id")
        self.assertEqual(asset.name, "Test Name")
        self.assertEqual(asset.category, AssetCategory.LETTER)
        self.assertEqual(asset.source_format, SourceFormat.PNG)
        self.assertEqual(asset.source_path, "path/to/source.png")
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
            name="Test Name",
            category=AssetCategory.LETTER,
            source_format=SourceFormat.PNG,
            source_path="path/to/source.png"
        )
        d = asset.to_dict()
        self.assertEqual(d["id"], "test_id")
        self.assertEqual(d["name"], "Test Name")
        self.assertEqual(d["category"], AssetCategory.LETTER.value)
        self.assertEqual(d["source_format"], SourceFormat.PNG.value)
        self.assertEqual(d["source_path"], "path/to/source.png")
        self.assertEqual(d["width"], 512)
        self.assertEqual(d["height"], 512)
        self.assertTrue(d["transparent_background"])
        self.assertIsNone(d["theme"])
        self.assertEqual(d["tags"], [])
        self.assertEqual(d["animation_compatible_presets"], [])
        self.assertEqual(d["export_targets"], [])
        self.assertEqual(d["notes"], "")

    def test_to_dict_full(self):
        asset = Asset(
            id="test_id_full",
            name="Test Name Full",
            category=AssetCategory.NUMBER,
            source_format=SourceFormat.SVG,
            source_path="path/to/source_full.svg",
            width=1024,
            height=768,
            transparent_background=False,
            theme=AssetTheme.NEON,
            tags=["tag1", "tag2"],
            animation_compatible_presets=["preset1"],
            export_targets=["gif"],
            notes="some notes"
        )
        d = asset.to_dict()
        self.assertEqual(d["id"], "test_id_full")
        self.assertEqual(d["name"], "Test Name Full")
        self.assertEqual(d["category"], AssetCategory.NUMBER.value)
        self.assertEqual(d["source_format"], SourceFormat.SVG.value)
        self.assertEqual(d["source_path"], "path/to/source_full.svg")
        self.assertEqual(d["width"], 1024)
        self.assertEqual(d["height"], 768)
        self.assertFalse(d["transparent_background"])
        self.assertEqual(d["theme"], AssetTheme.NEON.value)
        self.assertEqual(d["tags"], ["tag1", "tag2"])
        self.assertEqual(d["animation_compatible_presets"], ["preset1"])
        self.assertEqual(d["export_targets"], ["gif"])
        self.assertEqual(d["notes"], "some notes")

    def test_from_dict_minimal(self):
        data = {
            "id": "test_id",
            "name": "Test Name",
            "category": "letter",
            "source_format": "png",
            "source_path": "path/to/source.png"
        }
        asset = Asset.from_dict(data)
        self.assertEqual(asset.id, "test_id")
        self.assertEqual(asset.name, "Test Name")
        self.assertEqual(asset.category, AssetCategory.LETTER)
        self.assertEqual(asset.source_format, SourceFormat.PNG)
        self.assertEqual(asset.source_path, "path/to/source.png")
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
            "id": "test_id_full",
            "name": "Test Name Full",
            "category": "number",
            "source_format": "svg",
            "source_path": "path/to/source_full.svg",
            "width": 1024,
            "height": 768,
            "transparent_background": False,
            "theme": "neon",
            "tags": ["tag1", "tag2"],
            "animation_compatible_presets": ["preset1"],
            "export_targets": ["gif"],
            "notes": "some notes"
        }
        asset = Asset.from_dict(data)
        self.assertEqual(asset.id, "test_id_full")
        self.assertEqual(asset.name, "Test Name Full")
        self.assertEqual(asset.category, AssetCategory.NUMBER)
        self.assertEqual(asset.source_format, SourceFormat.SVG)
        self.assertEqual(asset.source_path, "path/to/source_full.svg")
        self.assertEqual(asset.width, 1024)
        self.assertEqual(asset.height, 768)
        self.assertFalse(asset.transparent_background)
        self.assertEqual(asset.theme, AssetTheme.NEON)
        self.assertEqual(asset.tags, ["tag1", "tag2"])
        self.assertEqual(asset.animation_compatible_presets, ["preset1"])
        self.assertEqual(asset.export_targets, ["gif"])
        self.assertEqual(asset.notes, "some notes")

if __name__ == "__main__":
    unittest.main()

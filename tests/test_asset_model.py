import unittest
from pipeline.asset_model import Asset, AssetCategory, SourceFormat, AssetTheme

class TestAssetModel(unittest.TestCase):
    def test_basic_instantiation(self):
        asset = Asset(
            id="letter_a",
            name="Letter A",
            category=AssetCategory.LETTER,
            source_format=SourceFormat.PNG,
            source_path="assets/source/letter_a.png"
        )
        self.assertEqual(asset.id, "letter_a")
        self.assertEqual(asset.name, "Letter A")
        self.assertEqual(asset.category, AssetCategory.LETTER)
        self.assertEqual(asset.source_format, SourceFormat.PNG)
        self.assertEqual(asset.source_path, "assets/source/letter_a.png")
        self.assertEqual(asset.width, 512)
        self.assertEqual(asset.height, 512)
        self.assertEqual(asset.transparent_background, True)
        self.assertEqual(asset.theme, None)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")

    def test_to_dict_all_fields(self):
        asset = Asset(
            id="symbol_cloud",
            name="Cloud Symbol",
            category=AssetCategory.SYMBOL,
            source_format=SourceFormat.SVG,
            source_path="assets/source/symbol_cloud.svg",
            width=1024,
            height=768,
            transparent_background=False,
            theme=AssetTheme.CLOUD,
            tags=["weather", "fluffy"],
            animation_compatible_presets=["float", "fade"],
            export_targets=["png", "webp"],
            notes="Use with care"
        )
        expected = {
            "id": "symbol_cloud",
            "name": "Cloud Symbol",
            "category": "symbol",
            "source_format": "svg",
            "source_path": "assets/source/symbol_cloud.svg",
            "width": 1024,
            "height": 768,
            "transparent_background": False,
            "theme": "cloud",
            "tags": ["weather", "fluffy"],
            "animation_compatible_presets": ["float", "fade"],
            "export_targets": ["png", "webp"],
            "notes": "Use with care"
        }
        self.assertEqual(asset.to_dict(), expected)

    def test_to_dict_missing_optional_fields(self):
        asset = Asset(
            id="letter_a",
            name="Letter A",
            category=AssetCategory.LETTER,
            source_format=SourceFormat.PNG,
            source_path="assets/source/letter_a.png"
        )
        data = asset.to_dict()
        self.assertEqual(data["theme"], None)
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["animation_compatible_presets"], [])
        self.assertEqual(data["export_targets"], [])
        self.assertEqual(data["notes"], "")
        self.assertEqual(data["width"], 512)
        self.assertEqual(data["height"], 512)
        self.assertEqual(data["transparent_background"], True)

    def test_from_dict_all_fields(self):
        data = {
            "id": "symbol_cloud",
            "name": "Cloud Symbol",
            "category": "symbol",
            "source_format": "svg",
            "source_path": "assets/source/symbol_cloud.svg",
            "width": 1024,
            "height": 768,
            "transparent_background": False,
            "theme": "cloud",
            "tags": ["weather", "fluffy"],
            "animation_compatible_presets": ["float", "fade"],
            "export_targets": ["png", "webp"],
            "notes": "Use with care"
        }
        asset = Asset.from_dict(data)
        self.assertEqual(asset.id, "symbol_cloud")
        self.assertEqual(asset.name, "Cloud Symbol")
        self.assertEqual(asset.category, AssetCategory.SYMBOL)
        self.assertEqual(asset.source_format, SourceFormat.SVG)
        self.assertEqual(asset.source_path, "assets/source/symbol_cloud.svg")
        self.assertEqual(asset.width, 1024)
        self.assertEqual(asset.height, 768)
        self.assertEqual(asset.transparent_background, False)
        self.assertEqual(asset.theme, AssetTheme.CLOUD)
        self.assertEqual(asset.tags, ["weather", "fluffy"])
        self.assertEqual(asset.animation_compatible_presets, ["float", "fade"])
        self.assertEqual(asset.export_targets, ["png", "webp"])
        self.assertEqual(asset.notes, "Use with care")

    def test_from_dict_missing_optional_fields(self):
        data = {
            "id": "letter_a",
            "name": "Letter A",
            "category": "letter",
            "source_format": "png",
            "source_path": "assets/source/letter_a.png"
        }
        asset = Asset.from_dict(data)
        self.assertEqual(asset.id, "letter_a")
        self.assertEqual(asset.theme, None)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")
        self.assertEqual(asset.width, 512)
        self.assertEqual(asset.height, 512)
        self.assertEqual(asset.transparent_background, True)

    def test_from_dict_invalid_category(self):
        data = {
            "id": "bad_asset",
            "name": "Bad Asset",
            "category": "invalid_category",
            "source_format": "png",
            "source_path": "assets/source/bad.png"
        }
        with self.assertRaises(ValueError):
            Asset.from_dict(data)

    def test_from_dict_invalid_source_format(self):
        data = {
            "id": "bad_asset",
            "name": "Bad Asset",
            "category": "letter",
            "source_format": "invalid_format",
            "source_path": "assets/source/bad.png"
        }
        with self.assertRaises(ValueError):
            Asset.from_dict(data)

    def test_from_dict_invalid_theme(self):
        data = {
            "id": "bad_asset",
            "name": "Bad Asset",
            "category": "letter",
            "source_format": "png",
            "source_path": "assets/source/bad.png",
            "theme": "invalid_theme"
        }
        with self.assertRaises(ValueError):
            Asset.from_dict(data)

if __name__ == '__main__':
    unittest.main()

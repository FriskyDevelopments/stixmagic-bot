import unittest
from typing import Any

from pipeline.asset_model import Asset, AssetCategory, AssetTheme, SourceFormat

class TestAssetModel(unittest.TestCase):
    def test_asset_defaults(self):
        """Test creating an Asset with minimum required fields and verify default values."""
        asset = Asset(
            id="letter_A",
            name="Letter A",
            category=AssetCategory.LETTER,
            source_format=SourceFormat.PNG,
            source_path="assets/source/letters/A.png"
        )

        self.assertEqual(asset.id, "letter_A")
        self.assertEqual(asset.name, "Letter A")
        self.assertEqual(asset.category, AssetCategory.LETTER)
        self.assertEqual(asset.source_format, SourceFormat.PNG)
        self.assertEqual(asset.source_path, "assets/source/letters/A.png")

        # Verify defaults
        self.assertEqual(asset.width, 512)
        self.assertEqual(asset.height, 512)
        self.assertTrue(asset.transparent_background)
        self.assertIsNone(asset.theme)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")

    def test_to_dict(self):
        """Verify that to_dict() correctly serializes an Asset with and without optional fields."""
        # Minimal asset
        min_asset = Asset(
            id="symbol_cloud",
            name="Cloud Symbol",
            category=AssetCategory.SYMBOL,
            source_format=SourceFormat.SVG,
            source_path="assets/source/symbols/cloud.svg"
        )

        min_dict = min_asset.to_dict()
        expected_min_dict = {
            "id": "symbol_cloud",
            "name": "Cloud Symbol",
            "category": "symbol",
            "source_format": "svg",
            "source_path": "assets/source/symbols/cloud.svg",
            "width": 512,
            "height": 512,
            "transparent_background": True,
            "theme": None,
            "tags": [],
            "animation_compatible_presets": [],
            "export_targets": [],
            "notes": ""
        }
        self.assertEqual(min_dict, expected_min_dict)

        # Full asset
        full_asset = Asset(
            id="dj_deck",
            name="DJ Deck",
            category=AssetCategory.ICON,
            source_format=SourceFormat.PNG,
            source_path="assets/source/icons/dj.png",
            width=1024,
            height=768,
            transparent_background=False,
            theme=AssetTheme.DJ,
            tags=["music", "party"],
            animation_compatible_presets=["pulse", "spin"],
            export_targets=["png", "webp"],
            notes="Requires manual optimization"
        )

        full_dict = full_asset.to_dict()
        expected_full_dict = {
            "id": "dj_deck",
            "name": "DJ Deck",
            "category": "icon",
            "source_format": "png",
            "source_path": "assets/source/icons/dj.png",
            "width": 1024,
            "height": 768,
            "transparent_background": False,
            "theme": "dj",
            "tags": ["music", "party"],
            "animation_compatible_presets": ["pulse", "spin"],
            "export_targets": ["png", "webp"],
            "notes": "Requires manual optimization"
        }
        self.assertEqual(full_dict, expected_full_dict)

    def test_from_dict(self):
        """Verify that from_dict() correctly deserializes a dictionary into an Asset."""
        # Minimal dict
        min_dict = {
            "id": "emoji_smile",
            "name": "Smile Emoji",
            "category": "emoji",
            "source_format": "webp",
            "source_path": "assets/source/emojis/smile.webp"
        }

        min_asset = Asset.from_dict(min_dict)
        self.assertEqual(min_asset.id, "emoji_smile")
        self.assertEqual(min_asset.name, "Smile Emoji")
        self.assertEqual(min_asset.category, AssetCategory.EMOJI)
        self.assertEqual(min_asset.source_format, SourceFormat.WEBP)
        self.assertEqual(min_asset.source_path, "assets/source/emojis/smile.webp")
        self.assertEqual(min_asset.width, 512)
        self.assertIsNone(min_asset.theme)

        # Full dict
        full_dict = {
            "id": "neon_sign",
            "name": "Neon Sign",
            "category": "overlay_element",
            "source_format": "gif",
            "source_path": "assets/source/overlays/neon.gif",
            "width": 800,
            "height": 600,
            "transparent_background": False,
            "theme": "neon",
            "tags": ["bright", "sign"],
            "animation_compatible_presets": ["flicker"],
            "export_targets": ["gif"],
            "notes": "Very bright"
        }

        full_asset = Asset.from_dict(full_dict)
        self.assertEqual(full_asset.id, "neon_sign")
        self.assertEqual(full_asset.width, 800)
        self.assertEqual(full_asset.transparent_background, False)
        self.assertEqual(full_asset.theme, AssetTheme.NEON)
        self.assertEqual(full_asset.tags, ["bright", "sign"])
        self.assertEqual(full_asset.animation_compatible_presets, ["flicker"])
        self.assertEqual(full_asset.export_targets, ["gif"])
        self.assertEqual(full_asset.notes, "Very bright")

    def test_from_dict_missing_fields(self):
        """Verify that from_dict() raises a KeyError when required fields are missing."""
        invalid_dict = {
            "name": "Missing ID",
            "category": "letter",
            "source_format": "png",
            "source_path": "path.png"
        }

        with self.assertRaises(KeyError):
            Asset.from_dict(invalid_dict)

    def test_from_dict_invalid_enum(self):
        """Verify that from_dict() raises a ValueError for invalid Enum values."""
        invalid_category_dict = {
            "id": "test",
            "name": "Test",
            "category": "invalid_category",
            "source_format": "png",
            "source_path": "path.png"
        }

        with self.assertRaises(ValueError):
            Asset.from_dict(invalid_category_dict)

        invalid_format_dict = {
            "id": "test",
            "name": "Test",
            "category": "letter",
            "source_format": "invalid_format",
            "source_path": "path.png"
        }

        with self.assertRaises(ValueError):
            Asset.from_dict(invalid_format_dict)

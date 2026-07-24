"""
Tests for pipeline/asset_model/__init__.py – Asset dataclass logic.

Covers:
 - Asset.to_dict() serialization
 - Asset.from_dict() deserialization
 - Default values handling
 - Enum conversions
"""

import unittest
from typing import Any

from pipeline.asset_model import Asset, AssetCategory, AssetTheme, SourceFormat


class TestAssetModel(unittest.TestCase):
    def setUp(self):
        self.mandatory_kwargs = {
            "id": "letter_A",
            "name": "Letter A",
            "category": AssetCategory.LETTER,
            "source_format": SourceFormat.PNG,
            "source_path": "assets/source/letters/A.png"
        }

    def test_asset_to_dict_mandatory_only(self):
        """Test serialization with only mandatory fields provided."""
        asset = Asset(**self.mandatory_kwargs)

        result = asset.to_dict()

        expected = {
            "id": "letter_A",
            "name": "Letter A",
            "category": "letter",
            "source_format": "png",
            "source_path": "assets/source/letters/A.png",
            "width": 512,
            "height": 512,
            "transparent_background": True,
            "theme": None,
            "tags": [],
            "animation_compatible_presets": [],
            "export_targets": [],
            "notes": ""
        }
        self.assertEqual(result, expected)

    def test_asset_from_dict_mandatory_only(self):
        """Test deserialization with only mandatory fields provided."""
        data = {
            "id": "letter_A",
            "name": "Letter A",
            "category": "letter",
            "source_format": "png",
            "source_path": "assets/source/letters/A.png"
        }

        asset = Asset.from_dict(data)

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

    def test_asset_to_dict_all_fields(self):
        """Test serialization with all fields populated."""
        asset = Asset(
            **self.mandatory_kwargs,
            width=1024,
            height=1024,
            transparent_background=False,
            theme=AssetTheme.NEON,
            tags=["neon", "glow"],
            animation_compatible_presets=["pulse", "shake"],
            export_targets=["gif", "webp"],
            notes="Requires extra glow"
        )

        result = asset.to_dict()

        expected = {
            "id": "letter_A",
            "name": "Letter A",
            "category": "letter",
            "source_format": "png",
            "source_path": "assets/source/letters/A.png",
            "width": 1024,
            "height": 1024,
            "transparent_background": False,
            "theme": "neon",
            "tags": ["neon", "glow"],
            "animation_compatible_presets": ["pulse", "shake"],
            "export_targets": ["gif", "webp"],
            "notes": "Requires extra glow"
        }
        self.assertEqual(result, expected)

    def test_asset_from_dict_all_fields(self):
        """Test deserialization with all fields populated."""
        data = {
            "id": "letter_A",
            "name": "Letter A",
            "category": "letter",
            "source_format": "png",
            "source_path": "assets/source/letters/A.png",
            "width": 1024,
            "height": 1024,
            "transparent_background": False,
            "theme": "neon",
            "tags": ["neon", "glow"],
            "animation_compatible_presets": ["pulse", "shake"],
            "export_targets": ["gif", "webp"],
            "notes": "Requires extra glow"
        }

        asset = Asset.from_dict(data)

        self.assertEqual(asset.width, 1024)
        self.assertEqual(asset.height, 1024)
        self.assertFalse(asset.transparent_background)
        self.assertEqual(asset.theme, AssetTheme.NEON)
        self.assertEqual(asset.tags, ["neon", "glow"])
        self.assertEqual(asset.animation_compatible_presets, ["pulse", "shake"])
        self.assertEqual(asset.export_targets, ["gif", "webp"])
        self.assertEqual(asset.notes, "Requires extra glow")

    def test_asset_roundtrip(self):
        """Test serialization and then deserialization results in identical object."""
        asset1 = Asset(
            **self.mandatory_kwargs,
            width=1024,
            height=1024,
            transparent_background=False,
            theme=AssetTheme.NEON,
            tags=["neon", "glow"],
            animation_compatible_presets=["pulse", "shake"],
            export_targets=["gif", "webp"],
            notes="Requires extra glow"
        )

        data = asset1.to_dict()
        asset2 = Asset.from_dict(data)

        self.assertEqual(asset1, asset2)


if __name__ == "__main__":
    unittest.main()

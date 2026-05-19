import unittest

from pipeline.asset_model.asset import Asset


class TestAsset(unittest.TestCase):
    def setUp(self):
        self.default_asset = Asset(
            id="letter_a_neon",
            name="Letter A",
            category="letter",
            theme="neon",
            source_format="png",
            source_path="letters/a_neon.png",
            width=100,
            height=100,
        )

        self.full_asset = Asset(
            id="emoji_smile_cloud",
            name="Smile",
            category="emoji",
            theme="cloud",
            source_format="webp",
            source_path="emojis/smile_cloud.webp",
            width=200,
            height=200,
            transparent_background=False,
            tags=["happy", "smile"],
            animation_compatible_presets=["bounce", "spin"],
            export_targets=["gif", "animated_webp"],
            notes="Testing notes",
        )

    def test_default_instantiation(self):
        """Test default values for optional fields."""
        asset = self.default_asset
        self.assertTrue(asset.transparent_background)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")

    def test_repr(self):
        """Test the string representation of Asset."""
        expected_repr = "<Asset id='letter_a_neon' category='letter' theme='neon'>"
        self.assertEqual(repr(self.default_asset), expected_repr)

    def test_is_animation_compatible(self):
        """Test preset compatibility logic."""
        # When animation_compatible_presets is empty, it should be compatible with everything
        self.assertTrue(self.default_asset.is_animation_compatible("any_preset"))

        # When populated, it should only be compatible with listed presets
        self.assertTrue(self.full_asset.is_animation_compatible("bounce"))
        self.assertFalse(self.full_asset.is_animation_compatible("shake"))

    def test_supports_export(self):
        """Test export target support logic."""
        # When export_targets is empty, it should support everything
        self.assertTrue(self.default_asset.supports_export("gif"))

        # When populated, it should only support listed targets
        self.assertTrue(self.full_asset.supports_export("gif"))
        self.assertFalse(self.full_asset.supports_export("png_sequence"))

    def test_to_dict(self):
        """Test serialisation to dictionary."""
        asset_dict = self.full_asset.to_dict()
        self.assertEqual(asset_dict["id"], "emoji_smile_cloud")
        self.assertEqual(asset_dict["name"], "Smile")
        self.assertEqual(asset_dict["category"], "emoji")
        self.assertEqual(asset_dict["theme"], "cloud")
        self.assertEqual(asset_dict["source_format"], "webp")
        self.assertEqual(asset_dict["source_path"], "emojis/smile_cloud.webp")
        self.assertEqual(asset_dict["width"], 200)
        self.assertEqual(asset_dict["height"], 200)
        self.assertFalse(asset_dict["transparent_background"])
        self.assertEqual(asset_dict["tags"], ["happy", "smile"])
        self.assertEqual(asset_dict["animation_compatible_presets"], ["bounce", "spin"])
        self.assertEqual(asset_dict["export_targets"], ["gif", "animated_webp"])
        self.assertEqual(asset_dict["notes"], "Testing notes")

    def test_from_dict(self):
        """Test deserialisation from dictionary."""
        data = {
            "id": "number_1_dj",
            "name": "One",
            "category": "number",
            "theme": "dj",
            "source_format": "svg",
            "source_path": "numbers/1_dj.svg",
            "width": 150,
            "height": 150,
            # Testing missing optional fields
        }

        asset = Asset.from_dict(data)

        self.assertEqual(asset.id, "number_1_dj")
        self.assertEqual(asset.name, "One")
        self.assertEqual(asset.category, "number")
        self.assertEqual(asset.theme, "dj")
        self.assertEqual(asset.source_format, "svg")
        self.assertEqual(asset.source_path, "numbers/1_dj.svg")
        self.assertEqual(asset.width, 150)
        self.assertEqual(asset.height, 150)
        # Check defaults
        self.assertTrue(asset.transparent_background)
        self.assertEqual(asset.tags, [])
        self.assertEqual(asset.animation_compatible_presets, [])
        self.assertEqual(asset.export_targets, [])
        self.assertEqual(asset.notes, "")


if __name__ == "__main__":
    unittest.main()

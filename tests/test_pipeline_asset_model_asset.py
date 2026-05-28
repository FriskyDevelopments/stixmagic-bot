import unittest

from pipeline.asset_model.asset import Asset, CATEGORY_LETTER, THEME_NEON, FORMAT_PNG

class TestAsset(unittest.TestCase):

    def _create_asset(self, animation_compatible_presets=None):
        kwargs = {
            "id": "test_asset",
            "name": "Test Asset",
            "category": CATEGORY_LETTER,
            "theme": THEME_NEON,
            "source_format": FORMAT_PNG,
            "source_path": "test.png",
            "width": 100,
            "height": 100,
        }
        if animation_compatible_presets is not None:
            kwargs["animation_compatible_presets"] = animation_compatible_presets

        return Asset(**kwargs)

    def test_is_animation_compatible_empty_presets(self):
        """When animation_compatible_presets is empty, it should return True for any preset."""
        asset = self._create_asset(animation_compatible_presets=[])
        self.assertTrue(asset.is_animation_compatible("any_preset"))
        self.assertTrue(asset.is_animation_compatible("another_preset"))

    def test_is_animation_compatible_preset_in_list(self):
        """When preset_id is in animation_compatible_presets, it should return True."""
        asset = self._create_asset(animation_compatible_presets=["allowed_preset1", "allowed_preset2"])
        self.assertTrue(asset.is_animation_compatible("allowed_preset1"))
        self.assertTrue(asset.is_animation_compatible("allowed_preset2"))

    def test_is_animation_compatible_preset_not_in_list(self):
        """When preset_id is not in animation_compatible_presets, it should return False."""
        asset = self._create_asset(animation_compatible_presets=["allowed_preset1", "allowed_preset2"])
        self.assertFalse(asset.is_animation_compatible("unallowed_preset"))
        self.assertFalse(asset.is_animation_compatible("another_unallowed"))

if __name__ == "__main__":
    unittest.main()

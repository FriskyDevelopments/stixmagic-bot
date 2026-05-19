import unittest

from pipeline.motion_presets.preset import MotionPreset
from pipeline.motion_presets import get_preset, list_presets, PRESET_REGISTRY, BUILTIN_PRESETS

class TestMotionPresets(unittest.TestCase):

    def test_get_preset_existing(self):
        """Test retrieving an existing preset."""
        preset = get_preset("pulse")
        self.assertIsNotNone(preset)
        self.assertEqual(preset.id, "pulse")
        self.assertEqual(preset.name, "Pulse")

    def test_get_preset_not_found(self):
        """Test retrieving a non-existing preset returns None."""
        preset = get_preset("non_existent_preset_id")
        self.assertIsNone(preset)

    def test_list_presets_no_filters(self):
        """Test listing presets with no filters returns all built-in presets."""
        presets = list_presets()
        self.assertEqual(len(presets), len(PRESET_REGISTRY))

    def test_list_presets_filter_by_category(self):
        """Test listing presets filtered by category."""
        expected_presets = [p for p in BUILTIN_PRESETS if not p.recommended_categories or "letter" in p.recommended_categories]
        presets = list_presets(category="letter")
        self.assertEqual(len(presets), len(expected_presets))
        self.assertListEqual(presets, expected_presets)

    def test_list_presets_filter_by_sticker_safe(self):
        """Test listing presets filtered by sticker_safe flag."""
        expected_presets_safe = [p for p in BUILTIN_PRESETS if p.sticker_safe]
        presets_safe = list_presets(sticker_safe=True)
        self.assertEqual(len(presets_safe), len(expected_presets_safe))
        self.assertListEqual(presets_safe, expected_presets_safe)

    def test_list_presets_filter_by_overlay_safe(self):
        """Test listing presets filtered by overlay_safe flag."""
        expected_presets_safe = [p for p in BUILTIN_PRESETS if p.overlay_safe]
        presets_safe = list_presets(overlay_safe=True)
        self.assertEqual(len(presets_safe), len(expected_presets_safe))
        self.assertListEqual(presets_safe, expected_presets_safe)

    def test_list_presets_combined_filters(self):
        """Test listing presets with multiple filters combined."""
        # Test category="particle" and sticker_safe=False
        expected_presets = [
            p for p in BUILTIN_PRESETS
            if (not p.recommended_categories or "particle" in p.recommended_categories) and p.sticker_safe is False
        ]
        presets = list_presets(category="particle", sticker_safe=False)
        self.assertEqual(len(presets), len(expected_presets))
        self.assertListEqual(presets, expected_presets)

    def test_motion_preset_to_dict(self):
        """Test serialization of MotionPreset to dict."""
        preset = MotionPreset(
            id="test_preset",
            name="Test Preset",
            loopable=False,
            duration_ms=5000,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["test"],
            parameter_schema={"param": {"type": "string"}},
            description="Test notes"
        )
        data = preset.to_dict()
        expected_data = {
            "id": "test_preset",
            "name": "Test Preset",
            "loopable": False,
            "duration_ms": 5000,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["test"],
            "parameter_schema": {"param": {"type": "string"}},
            "description": "Test notes"
        }
        self.assertDictEqual(data, expected_data)

    def test_motion_preset_from_dict(self):
        """Test deserialization of dict to MotionPreset."""
        data = {
            "id": "test_preset",
            "name": "Test Preset",
            "loopable": False,
            "duration_ms": 5000,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["test"],
            "parameter_schema": {"param": {"type": "string"}},
            "description": "Test notes"
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "test_preset")
        self.assertEqual(preset.name, "Test Preset")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration_ms, 5000)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertListEqual(preset.recommended_categories, ["test"])
        self.assertDictEqual(preset.parameter_schema, {"param": {"type": "string"}})
        self.assertEqual(preset.description, "Test notes")

    def test_motion_preset_from_dict_defaults(self):
        """Test deserialization of dict to MotionPreset with missing optional fields."""
        data = {
            "id": "test_preset",
            "name": "Test Preset"
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "test_preset")
        self.assertEqual(preset.name, "Test Preset")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertListEqual(preset.recommended_categories, [])
        self.assertDictEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

if __name__ == "__main__":
    unittest.main()

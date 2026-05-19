import unittest
from pipeline.motion_presets.preset import MotionPreset

class TestMotionPreset(unittest.TestCase):
    def test_initialization_defaults(self):
        preset = MotionPreset(id="test_id", name="Test Name")
        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Name")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

    def test_is_recommended_for(self):
        # Empty recommended_categories
        preset1 = MotionPreset(id="test1", name="Test 1")
        self.assertTrue(preset1.is_recommended_for("any_category"))

        # Specific recommended_categories
        preset2 = MotionPreset(id="test2", name="Test 2", recommended_categories=["cat1", "cat2"])
        self.assertTrue(preset2.is_recommended_for("cat1"))
        self.assertTrue(preset2.is_recommended_for("cat2"))
        self.assertFalse(preset2.is_recommended_for("cat3"))

    def test_to_dict_and_from_dict(self):
        original = MotionPreset(
            id="test_id",
            name="Test Name",
            loopable=False,
            duration_ms=500,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["cat1"],
            parameter_schema={"param1": "val1"},
            description="Test Description"
        )
        data = original.to_dict()
        expected_data = {
            "id": "test_id",
            "name": "Test Name",
            "loopable": False,
            "duration_ms": 500,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["cat1"],
            "parameter_schema": {"param1": "val1"},
            "description": "Test Description"
        }
        self.assertEqual(data, expected_data)

        restored = MotionPreset.from_dict(data)
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.loopable, original.loopable)
        self.assertEqual(restored.duration_ms, original.duration_ms)
        self.assertEqual(restored.alpha_safe, original.alpha_safe)
        self.assertEqual(restored.overlay_safe, original.overlay_safe)
        self.assertEqual(restored.sticker_safe, original.sticker_safe)
        self.assertEqual(restored.recommended_categories, original.recommended_categories)
        self.assertEqual(restored.parameter_schema, original.parameter_schema)
        self.assertEqual(restored.description, original.description)

    def test_repr(self):
        preset = MotionPreset(id="test_id", name="Test Name", duration_ms=1500, loopable=False)
        self.assertEqual(repr(preset), "<MotionPreset id='test_id' duration_ms=1500 loopable=False>")

if __name__ == '__main__':
    unittest.main()

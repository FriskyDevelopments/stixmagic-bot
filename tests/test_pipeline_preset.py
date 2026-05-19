import unittest
from pipeline.motion_presets.preset import MotionPreset

class TestMotionPreset(unittest.TestCase):
    def test_default_values(self):
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

    def test_is_recommended_for_empty_list(self):
        preset = MotionPreset(id="test_id", name="Test Name")
        self.assertTrue(preset.is_recommended_for("any_category"))

    def test_is_recommended_for_specific_category(self):
        preset = MotionPreset(id="test_id", name="Test Name", recommended_categories=["cat1", "cat2"])
        self.assertTrue(preset.is_recommended_for("cat1"))
        self.assertTrue(preset.is_recommended_for("cat2"))
        self.assertFalse(preset.is_recommended_for("cat3"))

    def test_to_dict(self):
        preset = MotionPreset(
            id="test_id",
            name="Test Name",
            loopable=False,
            duration_ms=2000,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["cat1"],
            parameter_schema={"param1": "value1"},
            description="Test description"
        )
        expected_dict = {
            "id": "test_id",
            "name": "Test Name",
            "loopable": False,
            "duration_ms": 2000,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["cat1"],
            "parameter_schema": {"param1": "value1"},
            "description": "Test description"
        }
        self.assertEqual(preset.to_dict(), expected_dict)

    def test_from_dict(self):
        data = {
            "id": "test_id",
            "name": "Test Name",
            "loopable": False,
            "duration_ms": 2000,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["cat1"],
            "parameter_schema": {"param1": "value1"},
            "description": "Test description"
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Name")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration_ms, 2000)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["cat1"])
        self.assertEqual(preset.parameter_schema, {"param1": "value1"})
        self.assertEqual(preset.description, "Test description")

    def test_from_dict_with_missing_optional_fields(self):
        data = {
            "id": "test_id",
            "name": "Test Name"
        }
        preset = MotionPreset.from_dict(data)
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

    def test_repr(self):
        preset = MotionPreset(id="test_id", name="Test Name", duration_ms=1500, loopable=False)
        self.assertEqual(repr(preset), "<MotionPreset id='test_id' duration_ms=1500 loopable=False>")

if __name__ == '__main__':
    unittest.main()

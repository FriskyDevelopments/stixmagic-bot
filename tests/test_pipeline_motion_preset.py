import unittest
from pipeline.motion_presets.preset import MotionPreset

class TestMotionPreset(unittest.TestCase):
    def test_is_recommended_for_empty(self):
        preset = MotionPreset(id="test", name="Test")
        # Empty list means it is compatible with all categories
        self.assertTrue(preset.is_recommended_for("any_category"))

    def test_is_recommended_for_specific(self):
        preset = MotionPreset(id="test", name="Test", recommended_categories=["cat1", "cat2"])
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
            recommended_categories=["cat"],
            parameter_schema={"param": "value"},
            description="Test Desc",
        )
        data = preset.to_dict()
        self.assertEqual(data["id"], "test_id")
        self.assertEqual(data["name"], "Test Name")
        self.assertEqual(data["loopable"], False)
        self.assertEqual(data["duration_ms"], 2000)
        self.assertEqual(data["alpha_safe"], False)
        self.assertEqual(data["overlay_safe"], False)
        self.assertEqual(data["sticker_safe"], False)
        self.assertEqual(data["recommended_categories"], ["cat"])
        self.assertEqual(data["parameter_schema"], {"param": "value"})
        self.assertEqual(data["description"], "Test Desc")

    def test_from_dict_complete(self):
        data = {
            "id": "test_id",
            "name": "Test Name",
            "loopable": False,
            "duration_ms": 2000,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["cat"],
            "parameter_schema": {"param": "value"},
            "description": "Test Desc",
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Name")
        self.assertEqual(preset.loopable, False)
        self.assertEqual(preset.duration_ms, 2000)
        self.assertEqual(preset.alpha_safe, False)
        self.assertEqual(preset.overlay_safe, False)
        self.assertEqual(preset.sticker_safe, False)
        self.assertEqual(preset.recommended_categories, ["cat"])
        self.assertEqual(preset.parameter_schema, {"param": "value"})
        self.assertEqual(preset.description, "Test Desc")

    def test_from_dict_defaults(self):
        data = {
            "id": "test_id",
            "name": "Test Name"
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Name")
        self.assertEqual(preset.loopable, True)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertEqual(preset.alpha_safe, True)
        self.assertEqual(preset.overlay_safe, True)
        self.assertEqual(preset.sticker_safe, True)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

    def test_repr(self):
        preset = MotionPreset(id="test_id", name="Test Name", duration_ms=1500, loopable=False)
        rep = repr(preset)
        self.assertIn("test_id", rep)
        self.assertIn("1500", rep)
        self.assertIn("False", rep)

if __name__ == "__main__":
    unittest.main()

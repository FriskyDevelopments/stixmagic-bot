import unittest
from pipeline.motion_presets.preset import MotionPreset

class TestMotionPreset(unittest.TestCase):
    def test_default_initialization(self):
        preset = MotionPreset(id="test_id", name="Test Preset")
        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Preset")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

    def test_custom_initialization(self):
        preset = MotionPreset(
            id="pulse",
            name="Pulse Effect",
            loopable=False,
            duration_ms=500,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["avatar", "reaction"],
            parameter_schema={"scale": {"type": "number"}},
            description="A pulse effect"
        )
        self.assertEqual(preset.id, "pulse")
        self.assertEqual(preset.name, "Pulse Effect")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration_ms, 500)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["avatar", "reaction"])
        self.assertEqual(preset.parameter_schema, {"scale": {"type": "number"}})
        self.assertEqual(preset.description, "A pulse effect")

    def test_is_recommended_for_empty_categories(self):
        preset = MotionPreset(id="test", name="Test")
        self.assertTrue(preset.is_recommended_for("any_category"))

    def test_is_recommended_for_matching_category(self):
        preset = MotionPreset(id="test", name="Test", recommended_categories=["avatar", "emoji"])
        self.assertTrue(preset.is_recommended_for("avatar"))
        self.assertTrue(preset.is_recommended_for("emoji"))

    def test_is_recommended_for_non_matching_category(self):
        preset = MotionPreset(id="test", name="Test", recommended_categories=["avatar", "emoji"])
        self.assertFalse(preset.is_recommended_for("reaction"))

    def test_to_dict(self):
        preset = MotionPreset(
            id="pulse",
            name="Pulse Effect",
            loopable=False,
            duration_ms=500,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["avatar"],
            parameter_schema={"scale": {"type": "number"}},
            description="A pulse effect"
        )
        expected = {
            "id": "pulse",
            "name": "Pulse Effect",
            "loopable": False,
            "duration_ms": 500,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["avatar"],
            "parameter_schema": {"scale": {"type": "number"}},
            "description": "A pulse effect",
        }
        self.assertEqual(preset.to_dict(), expected)

    def test_from_dict_all_attributes(self):
        data = {
            "id": "pulse",
            "name": "Pulse Effect",
            "loopable": False,
            "duration_ms": 500,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["avatar"],
            "parameter_schema": {"scale": {"type": "number"}},
            "description": "A pulse effect",
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "pulse")
        self.assertEqual(preset.name, "Pulse Effect")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration_ms, 500)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["avatar"])
        self.assertEqual(preset.parameter_schema, {"scale": {"type": "number"}})
        self.assertEqual(preset.description, "A pulse effect")

    def test_from_dict_required_attributes_only(self):
        data = {
            "id": "test_id",
            "name": "Test Preset",
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Preset")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

    def test_repr(self):
        preset = MotionPreset(id="test_id", name="Test Preset", duration_ms=2000, loopable=False)
        self.assertEqual(repr(preset), "<MotionPreset id='test_id' duration_ms=2000 loopable=False>")

if __name__ == '__main__':
    unittest.main()

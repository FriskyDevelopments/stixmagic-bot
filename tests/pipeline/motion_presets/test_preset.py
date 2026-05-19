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
            name="Pulse",
            loopable=False,
            duration_ms=500,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["emojis"],
            parameter_schema={"scale": {"type": "number"}},
            description="A pulse effect"
        )
        self.assertEqual(preset.id, "pulse")
        self.assertEqual(preset.name, "Pulse")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration_ms, 500)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["emojis"])
        self.assertEqual(preset.parameter_schema, {"scale": {"type": "number"}})
        self.assertEqual(preset.description, "A pulse effect")

    def test_is_recommended_for_empty_categories(self):
        preset = MotionPreset(id="test", name="Test")
        # Should be recommended for any category if recommended_categories is empty
        self.assertTrue(preset.is_recommended_for("emojis"))
        self.assertTrue(preset.is_recommended_for("stickers"))
        self.assertTrue(preset.is_recommended_for("anything"))

    def test_is_recommended_for_specific_categories(self):
        preset = MotionPreset(id="test", name="Test", recommended_categories=["emojis", "reactions"])
        self.assertTrue(preset.is_recommended_for("emojis"))
        self.assertTrue(preset.is_recommended_for("reactions"))
        self.assertFalse(preset.is_recommended_for("stickers"))

    def test_to_dict(self):
        preset = MotionPreset(
            id="shake",
            name="Shake",
            loopable=False,
            duration_ms=200,
            alpha_safe=True,
            overlay_safe=False,
            sticker_safe=True,
            recommended_categories=["reactions"],
            parameter_schema={"intensity": {"type": "number"}},
            description="Shakes the asset"
        )

        expected_dict = {
            "id": "shake",
            "name": "Shake",
            "loopable": False,
            "duration_ms": 200,
            "alpha_safe": True,
            "overlay_safe": False,
            "sticker_safe": True,
            "recommended_categories": ["reactions"],
            "parameter_schema": {"intensity": {"type": "number"}},
            "description": "Shakes the asset",
        }

        self.assertEqual(preset.to_dict(), expected_dict)

    def test_from_dict_minimal(self):
        data = {
            "id": "minimal",
            "name": "Minimal Preset"
        }
        preset = MotionPreset.from_dict(data)

        self.assertEqual(preset.id, "minimal")
        self.assertEqual(preset.name, "Minimal Preset")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

    def test_from_dict_full(self):
        data = {
            "id": "full",
            "name": "Full Preset",
            "loopable": False,
            "duration_ms": 300,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["avatars"],
            "parameter_schema": {"speed": {"type": "number"}},
            "description": "Full preset description"
        }
        preset = MotionPreset.from_dict(data)

        self.assertEqual(preset.id, "full")
        self.assertEqual(preset.name, "Full Preset")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration_ms, 300)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["avatars"])
        self.assertEqual(preset.parameter_schema, {"speed": {"type": "number"}})
        self.assertEqual(preset.description, "Full preset description")

    def test_repr(self):
        preset = MotionPreset(id="bounce", name="Bounce", duration_ms=1200, loopable=True)
        self.assertEqual(repr(preset), "<MotionPreset id='bounce' duration_ms=1200 loopable=True>")

        preset2 = MotionPreset(id="fade", name="Fade", duration_ms=800, loopable=False)
        self.assertEqual(repr(preset2), "<MotionPreset id='fade' duration_ms=800 loopable=False>")

if __name__ == '__main__':
    unittest.main()

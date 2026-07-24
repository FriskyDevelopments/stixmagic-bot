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

    def test_is_recommended_for(self):
        # When recommended_categories is empty, it works for all
        preset_empty = MotionPreset(id="1", name="1", recommended_categories=[])
        self.assertTrue(preset_empty.is_recommended_for("any_category"))

        preset_specific = MotionPreset(
            id="2", name="2", recommended_categories=["cat1", "cat2"]
        )
        self.assertTrue(preset_specific.is_recommended_for("cat1"))
        self.assertTrue(preset_specific.is_recommended_for("cat2"))
        self.assertFalse(preset_specific.is_recommended_for("cat3"))

    def test_to_dict(self):
        preset = MotionPreset(
            id="pulse",
            name="Pulse",
            loopable=False,
            duration_ms=500,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["cat1"],
            parameter_schema={"param1": "val1"},
            description="Pulse effect",
        )

        expected_dict = {
            "id": "pulse",
            "name": "Pulse",
            "loopable": False,
            "duration_ms": 500,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["cat1"],
            "parameter_schema": {"param1": "val1"},
            "description": "Pulse effect",
        }

        self.assertEqual(preset.to_dict(), expected_dict)

    def test_from_dict(self):
        data = {
            "id": "glow",
            "name": "Glow",
            "loopable": True,
            "duration_ms": 2000,
            "alpha_safe": True,
            "overlay_safe": True,
            "sticker_safe": True,
            "recommended_categories": ["cat2"],
            "parameter_schema": {"param2": "val2"},
            "description": "Glow effect",
        }

        preset = MotionPreset.from_dict(data)

        self.assertEqual(preset.id, "glow")
        self.assertEqual(preset.name, "Glow")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 2000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["cat2"])
        self.assertEqual(preset.parameter_schema, {"param2": "val2"})
        self.assertEqual(preset.description, "Glow effect")

    def test_from_dict_with_missing_optional_fields(self):
        data = {"id": "minimal", "name": "Minimal"}

        preset = MotionPreset.from_dict(data)

        self.assertEqual(preset.id, "minimal")
        self.assertEqual(preset.name, "Minimal")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

    def test_repr(self):
        preset = MotionPreset(
            id="test_repr", name="Name", duration_ms=1234, loopable=False
        )
        self.assertEqual(
            repr(preset),
            "<MotionPreset id='test_repr' duration_ms=1234 loopable=False>",
        )


if __name__ == "__main__":
    unittest.main()

import unittest
from pipeline.motion_presets.preset import MotionPreset

class TestMotionPreset(unittest.TestCase):
    def test_initialization(self):
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

    def test_is_recommended_for(self):
        preset1 = MotionPreset(id="p1", name="P1")
        self.assertTrue(preset1.is_recommended_for("any"))

        preset2 = MotionPreset(id="p2", name="P2", recommended_categories=["cat1", "cat2"])
        self.assertTrue(preset2.is_recommended_for("cat1"))
        self.assertFalse(preset2.is_recommended_for("cat3"))

    def test_to_dict(self):
        preset = MotionPreset(
            id="p1",
            name="P1",
            loopable=False,
            duration_ms=2000,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["cat1"],
            parameter_schema={"param1": "type"},
            description="Desc"
        )
        d = preset.to_dict()
        self.assertEqual(d["id"], "p1")
        self.assertEqual(d["name"], "P1")
        self.assertFalse(d["loopable"])
        self.assertEqual(d["duration_ms"], 2000)
        self.assertFalse(d["alpha_safe"])
        self.assertFalse(d["overlay_safe"])
        self.assertFalse(d["sticker_safe"])
        self.assertEqual(d["recommended_categories"], ["cat1"])
        self.assertEqual(d["parameter_schema"], {"param1": "type"})
        self.assertEqual(d["description"], "Desc")

    def test_from_dict_full(self):
        data = {
            "id": "full_id",
            "name": "Full Name",
            "loopable": False,
            "duration_ms": 500,
            "alpha_safe": False,
            "overlay_safe": False,
            "sticker_safe": False,
            "recommended_categories": ["cat1"],
            "parameter_schema": {"param1": "type"},
            "description": "Desc"
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "full_id")
        self.assertEqual(preset.name, "Full Name")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration_ms, 500)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["cat1"])
        self.assertEqual(preset.parameter_schema, {"param1": "type"})
        self.assertEqual(preset.description, "Desc")

    def test_from_dict_partial(self):
        data = {
            "id": "partial_id",
            "name": "Partial Name"
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "partial_id")
        self.assertEqual(preset.name, "Partial Name")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration_ms, 1000)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.description, "")

    def test_repr(self):
        preset = MotionPreset(id="p1", name="P1", duration_ms=2000, loopable=False)
        rep = repr(preset)
        self.assertIn("id='p1'", rep)
        self.assertIn("duration_ms=2000", rep)
        self.assertIn("loopable=False", rep)

if __name__ == '__main__':
    unittest.main()

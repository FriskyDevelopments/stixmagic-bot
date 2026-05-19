import unittest
from unittest import mock
import sys

class TestPipelineMotionPresets(unittest.TestCase):

    def test_motion_preset_dataclass(self):
        from pipeline.motion_presets.preset import MotionPreset
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

    def test_motion_preset_is_recommended_for(self):
        from pipeline.motion_presets.preset import MotionPreset
        preset = MotionPreset(id="test", name="test", recommended_categories=["emoji", "icon"])
        self.assertTrue(preset.is_recommended_for("emoji"))
        self.assertTrue(preset.is_recommended_for("icon"))
        self.assertFalse(preset.is_recommended_for("letter"))

        # Empty list means it is compatible with all categories
        preset_all = MotionPreset(id="test_all", name="test_all")
        self.assertTrue(preset_all.is_recommended_for("emoji"))
        self.assertTrue(preset_all.is_recommended_for("anything"))

    def test_motion_preset_to_dict_and_from_dict(self):
        from pipeline.motion_presets.preset import MotionPreset
        preset = MotionPreset(
            id="test_id",
            name="Test Preset",
            loopable=False,
            duration_ms=3500,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["icon", "symbol"],
            parameter_schema={"speed": {"type": "float", "default": 1.0}},
            description="Testing to/from dict",
        )

        data = preset.to_dict()
        self.assertEqual(data["id"], "test_id")
        self.assertEqual(data["name"], "Test Preset")
        self.assertFalse(data["loopable"])
        self.assertEqual(data["duration_ms"], 3500)
        self.assertFalse(data["alpha_safe"])
        self.assertFalse(data["overlay_safe"])
        self.assertFalse(data["sticker_safe"])
        self.assertEqual(data["recommended_categories"], ["icon", "symbol"])
        self.assertEqual(data["parameter_schema"], {"speed": {"type": "float", "default": 1.0}})
        self.assertEqual(data["description"], "Testing to/from dict")

        restored_preset = MotionPreset.from_dict(data)
        self.assertEqual(restored_preset.id, preset.id)
        self.assertEqual(restored_preset.name, preset.name)
        self.assertEqual(restored_preset.loopable, preset.loopable)
        self.assertEqual(restored_preset.duration_ms, preset.duration_ms)
        self.assertEqual(restored_preset.alpha_safe, preset.alpha_safe)
        self.assertEqual(restored_preset.overlay_safe, preset.overlay_safe)
        self.assertEqual(restored_preset.sticker_safe, preset.sticker_safe)
        self.assertEqual(restored_preset.recommended_categories, preset.recommended_categories)
        self.assertEqual(restored_preset.parameter_schema, preset.parameter_schema)
        self.assertEqual(restored_preset.description, preset.description)

    def test_catalog_get_preset(self):
        from pipeline.motion_presets import get_preset, PRESET_REGISTRY
        from pipeline.motion_presets.catalog import get_preset as catalog_get_preset, PRESETS

        # Test __init__'s get_preset
        first_key = list(PRESET_REGISTRY.keys())[0]
        preset = get_preset(first_key)
        self.assertEqual(preset.id, first_key)
        self.assertIsNone(get_preset("non_existent_preset_123"))

        # Test catalog's get_preset
        preset_cat = catalog_get_preset(first_key)
        self.assertEqual(preset_cat.id, first_key)
        with self.assertRaises(KeyError):
            catalog_get_preset("non_existent_preset_123")

    def test_catalog_list_presets(self):
        from pipeline.motion_presets import list_presets, PRESET_REGISTRY

        all_presets = list_presets()
        self.assertEqual(len(all_presets), len(PRESET_REGISTRY))

    def test_fallback_list_presets(self):
        # We need to test the fallback version of `list_presets` in `__init__.py`
        import importlib.util

        spec = importlib.util.spec_from_file_location("pipeline.motion_presets", "pipeline/motion_presets/__init__.py")
        module = importlib.util.module_from_spec(spec)

        with mock.patch.dict('sys.modules'):
            sys.modules['pipeline.motion_presets'] = module
            sys.modules['pipeline.motion_presets.catalog'] = None
            spec.loader.exec_module(module)

            # Test unfiltered
            all_presets = module.list_presets()
            self.assertEqual(len(all_presets), len(module.BUILTIN_PRESETS))

            # Test filtering by category
            emoji_presets = module.list_presets(category="emoji")
            self.assertTrue(len(emoji_presets) > 0)
            for p in emoji_presets:
                self.assertTrue(not p.recommended_categories or "emoji" in p.recommended_categories)

            # Test sticker_safe filter
            sticker_safe_presets = module.list_presets(sticker_safe=True)
            for p in sticker_safe_presets:
                self.assertTrue(p.sticker_safe)

            non_sticker_safe_presets = module.list_presets(sticker_safe=False)
            for p in non_sticker_safe_presets:
                self.assertFalse(p.sticker_safe)

            # Test overlay_safe filter
            overlay_safe_presets = module.list_presets(overlay_safe=True)
            for p in overlay_safe_presets:
                self.assertTrue(p.overlay_safe)

            # Test combined filters
            combined_presets = module.list_presets(sticker_safe=True, overlay_safe=True)
            for p in combined_presets:
                self.assertTrue(p.sticker_safe)
                self.assertTrue(p.overlay_safe)

if __name__ == '__main__':
    unittest.main()

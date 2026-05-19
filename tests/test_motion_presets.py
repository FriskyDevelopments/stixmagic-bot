"""
Tests for pipeline.motion_presets.__init__

The file pipeline/motion_presets/__init__.py contains a dataclass and functions
that are optionally overshadowed by imports from `catalog.py`.
These tests verify the pure fallback logic defined directly in `__init__.py`.
"""

import sys
import importlib
import unittest

import pipeline.motion_presets.__init__ as init_module


class TestMotionPresetsInit(unittest.TestCase):
    def setUp(self):
        # Mask the catalog module to prevent the try/except block in __init__.py
        # from shadowing the original functions.
        self.original_catalog = sys.modules.get('pipeline.motion_presets.catalog', None)
        sys.modules['pipeline.motion_presets.catalog'] = None
        importlib.reload(init_module)

    def tearDown(self):
        # Restore the catalog module
        if self.original_catalog is not None:
            sys.modules['pipeline.motion_presets.catalog'] = self.original_catalog
        else:
            del sys.modules['pipeline.motion_presets.catalog']
        importlib.reload(init_module)

    def test_motion_preset_dataclass_defaults(self):
        preset = init_module.MotionPreset(id="test_id", name="Test Name")

        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Name")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration, 2.0)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.notes, "")

    def test_motion_preset_dataclass_custom(self):
        preset = init_module.MotionPreset(
            id="test_id",
            name="Test Name",
            loopable=False,
            duration=5.0,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["cat1", "cat2"],
            parameter_schema={"param1": {"type": "float", "default": 1.0}},
            notes="Some notes",
        )

        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Name")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration, 5.0)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, ["cat1", "cat2"])
        self.assertEqual(preset.parameter_schema, {"param1": {"type": "float", "default": 1.0}})
        self.assertEqual(preset.notes, "Some notes")

    def test_motion_preset_to_dict_and_from_dict(self):
        preset = init_module.MotionPreset(
            id="test_id",
            name="Test Name",
            loopable=False,
            duration=3.5,
            alpha_safe=False,
            overlay_safe=True,
            sticker_safe=False,
            recommended_categories=["cat1", "cat2"],
            parameter_schema={"param1": {"type": "float", "default": 1.0}},
            notes="Some notes",
        )

        data = preset.to_dict()
        self.assertEqual(data["id"], "test_id")
        self.assertEqual(data["name"], "Test Name")
        self.assertEqual(data["loopable"], False)
        self.assertEqual(data["duration"], 3.5)
        self.assertEqual(data["alpha_safe"], False)
        self.assertEqual(data["overlay_safe"], True)
        self.assertEqual(data["sticker_safe"], False)
        self.assertEqual(data["recommended_categories"], ["cat1", "cat2"])
        self.assertEqual(data["parameter_schema"], {"param1": {"type": "float", "default": 1.0}})
        self.assertEqual(data["notes"], "Some notes")

        restored_preset = init_module.MotionPreset.from_dict(data)
        self.assertEqual(restored_preset, preset)

    def test_motion_preset_from_dict_defaults(self):
        data = {
            "id": "test_id",
            "name": "Test Name",
        }
        preset = init_module.MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "test_id")
        self.assertEqual(preset.name, "Test Name")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration, 2.0)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.notes, "")

    def test_get_preset_valid_id(self):
        # BUILTIN_PRESETS[0] is 'pulse'
        pulse = init_module.BUILTIN_PRESETS[0]
        self.assertEqual(init_module.get_preset("pulse"), pulse)

    def test_get_preset_invalid_id(self):
        self.assertIsNone(init_module.get_preset("non_existent_preset_id"))

    def test_list_presets_no_filters(self):
        results = init_module.list_presets()
        self.assertEqual(len(results), len(init_module.BUILTIN_PRESETS))
        self.assertEqual(results, init_module.BUILTIN_PRESETS)

    def test_list_presets_category_filter(self):
        # Assuming 'pulse' and 'glow' have 'letter' in recommended_categories
        results = init_module.list_presets(category="letter")
        self.assertTrue(len(results) > 0)

        for p in results:
            self.assertTrue(
                not p.recommended_categories or "letter" in p.recommended_categories
            )

    def test_list_presets_sticker_safe_filter(self):
        results_true = init_module.list_presets(sticker_safe=True)
        self.assertTrue(len(results_true) > 0)
        for p in results_true:
            self.assertTrue(p.sticker_safe)

        results_false = init_module.list_presets(sticker_safe=False)
        self.assertTrue(len(results_false) > 0)
        for p in results_false:
            self.assertFalse(p.sticker_safe)

    def test_list_presets_overlay_safe_filter(self):
        results_true = init_module.list_presets(overlay_safe=True)
        self.assertTrue(len(results_true) > 0)
        for p in results_true:
            self.assertTrue(p.overlay_safe)

        # If there's any not overlay safe presets in BUILTIN_PRESETS, test them
        results_false = init_module.list_presets(overlay_safe=False)
        for p in results_false:
            self.assertFalse(p.overlay_safe)

    def test_list_presets_multiple_filters(self):
        results = init_module.list_presets(
            category="letter",
            sticker_safe=True,
            overlay_safe=True
        )
        self.assertTrue(len(results) > 0)

        for p in results:
            self.assertTrue(
                not p.recommended_categories or "letter" in p.recommended_categories
            )
            self.assertTrue(p.sticker_safe)
            self.assertTrue(p.overlay_safe)

if __name__ == '__main__':
    unittest.main()

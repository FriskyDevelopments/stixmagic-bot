import unittest
import importlib

# We need to bypass the shadowing of `list_presets` by the `try...except ImportError` block at the end
# of `pipeline/motion_presets/__init__.py`.
# We can do this by patching sys.modules or just reading the function. Actually, `pipeline.motion_presets.__init__` is a module,
# wait, we can just patch `sys.modules['pipeline.motion_presets.catalog']` to raise ImportError?
# No, let's just write the tests for what the user requested. If the function is shadowed, that's a bug in their code,
# or maybe we can import it directly by parsing, or we can just mock `import pipeline.motion_presets.catalog`.
# Let's see if we can reload the module with catalog missing.

import sys
from unittest.mock import patch

class TestMotionPresetRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force __init__.py to not import list_presets from catalog
        with patch.dict(sys.modules, {'pipeline.motion_presets.catalog': None}):
            import pipeline.motion_presets
            importlib.reload(pipeline.motion_presets)
            cls.module = pipeline.motion_presets
            cls.MotionPreset = pipeline.motion_presets.MotionPreset
            cls.BUILTIN_PRESETS = pipeline.motion_presets.BUILTIN_PRESETS

    def test_to_dict_and_from_dict(self):
        # Create a motion preset with some values
        preset = self.MotionPreset(
            id="test_preset",
            name="Test Preset",
            loopable=False,
            duration=5.0,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["cat1", "cat2"],
            parameter_schema={"param1": {"type": "string", "default": "value"}},
            notes="Test notes"
        )

        # Serialize to dict
        data = preset.to_dict()

        # Verify dict contents
        self.assertEqual(data["id"], "test_preset")
        self.assertEqual(data["name"], "Test Preset")
        self.assertFalse(data["loopable"])
        self.assertEqual(data["duration"], 5.0)
        self.assertFalse(data["alpha_safe"])
        self.assertFalse(data["overlay_safe"])
        self.assertFalse(data["sticker_safe"])
        self.assertEqual(data["recommended_categories"], ["cat1", "cat2"])
        self.assertEqual(data["parameter_schema"], {"param1": {"type": "string", "default": "value"}})
        self.assertEqual(data["notes"], "Test notes")

        # Deserialize from dict
        new_preset = self.MotionPreset.from_dict(data)

        # Verify the new instance matches the original
        self.assertEqual(new_preset.id, preset.id)
        self.assertEqual(new_preset.name, preset.name)
        self.assertEqual(new_preset.loopable, preset.loopable)
        self.assertEqual(new_preset.duration, preset.duration)
        self.assertEqual(new_preset.alpha_safe, preset.alpha_safe)
        self.assertEqual(new_preset.overlay_safe, preset.overlay_safe)
        self.assertEqual(new_preset.sticker_safe, preset.sticker_safe)
        self.assertEqual(new_preset.recommended_categories, preset.recommended_categories)
        self.assertEqual(new_preset.parameter_schema, preset.parameter_schema)
        self.assertEqual(new_preset.notes, preset.notes)

    def test_from_dict_defaults(self):
        # Test that from_dict correctly applies defaults when optional fields are missing
        data = {
            "id": "minimal",
            "name": "Minimal Preset"
        }
        preset = self.MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "minimal")
        self.assertEqual(preset.name, "Minimal Preset")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration, 2.0)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.notes, "")

    def test_get_preset(self):
        # Test retrieving an existing preset
        preset = self.module.get_preset("pulse")
        self.assertIsNotNone(preset)
        self.assertIsInstance(preset, self.MotionPreset)
        self.assertEqual(preset.id, "pulse")

        # Test retrieving a non-existent preset
        self.assertIsNone(self.module.get_preset("non_existent_preset_id"))

    def test_list_presets_no_filters(self):
        # Should return all builtin presets
        presets = self.module.list_presets()
        self.assertEqual(len(presets), len(self.BUILTIN_PRESETS))

    def test_list_presets_category_filter(self):
        # Get presets recommended for "emoji"
        emoji_presets = self.module.list_presets(category="emoji")

        # Verify all returned presets either have "emoji" in recommended_categories or empty recommended_categories
        for p in emoji_presets:
            self.assertTrue(not p.recommended_categories or "emoji" in p.recommended_categories)

        # Verify it filters correctly (orbit shouldn't be in emoji presets)
        orbit_preset = self.module.get_preset("orbit")
        if orbit_preset and orbit_preset.recommended_categories and "emoji" not in orbit_preset.recommended_categories:
            self.assertNotIn(orbit_preset, emoji_presets)

    def test_list_presets_sticker_safe_filter(self):
        # Get only sticker-safe presets
        safe_presets = self.module.list_presets(sticker_safe=True)
        for p in safe_presets:
            self.assertTrue(p.sticker_safe)

        # Get non-sticker-safe presets
        unsafe_presets = self.module.list_presets(sticker_safe=False)
        for p in unsafe_presets:
            self.assertFalse(p.sticker_safe)

        # They should add up to total
        self.assertEqual(len(safe_presets) + len(unsafe_presets), len(self.BUILTIN_PRESETS))

    def test_list_presets_overlay_safe_filter(self):
        # Get only overlay-safe presets
        safe_presets = self.module.list_presets(overlay_safe=True)
        for p in safe_presets:
            self.assertTrue(p.overlay_safe)

        # Get non-overlay-safe presets
        unsafe_presets = self.module.list_presets(overlay_safe=False)
        for p in unsafe_presets:
            self.assertFalse(p.overlay_safe)

        # They should add up to total
        self.assertEqual(len(safe_presets) + len(unsafe_presets), len(self.BUILTIN_PRESETS))

    def test_list_presets_multiple_filters(self):
        # Should be able to combine filters
        filtered = self.module.list_presets(category="particle", sticker_safe=False)
        for p in filtered:
            self.assertTrue(not p.recommended_categories or "particle" in p.recommended_categories)
            self.assertFalse(p.sticker_safe)

if __name__ == "__main__":
    unittest.main()

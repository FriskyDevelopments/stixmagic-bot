import unittest

from pipeline.motion_presets.catalog import PRESETS, get_preset, list_presets
from pipeline.motion_presets.preset import MotionPreset


class TestMotionPresetsCatalog(unittest.TestCase):
    def test_presets_dict(self):
        self.assertIsInstance(PRESETS, dict)
        self.assertTrue(len(PRESETS) > 0)
        for key, preset in PRESETS.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(preset, MotionPreset)
            self.assertEqual(key, preset.id)

    def test_get_preset_success(self):
        preset_id = list(PRESETS.keys())[0]
        preset = get_preset(preset_id)
        self.assertIsInstance(preset, MotionPreset)
        self.assertEqual(preset.id, preset_id)

    def test_get_preset_failure(self):
        with self.assertRaises(KeyError) as context:
            get_preset("invalid_preset_id_that_does_not_exist")
        self.assertIn("Unknown motion preset", str(context.exception))

    def test_list_presets(self):
        presets_list = list_presets()
        self.assertIsInstance(presets_list, list)
        self.assertEqual(len(presets_list), len(PRESETS))
        for preset in presets_list:
            self.assertIsInstance(preset, MotionPreset)

        # Verify the list contents match the dictionary values
        self.assertEqual(presets_list, list(PRESETS.values()))

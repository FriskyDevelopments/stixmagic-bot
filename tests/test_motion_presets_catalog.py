import unittest

from pipeline.motion_presets.catalog import PRESETS, get_preset, list_presets
from pipeline.motion_presets.preset import MotionPreset

class TestMotionPresetsCatalog(unittest.TestCase):

    def test_get_preset_existing(self):
        """Test get_preset returns the correct preset for a valid ID."""
        # Grab the first preset from the PRESETS dictionary
        valid_id = list(PRESETS.keys())[0]
        preset = get_preset(valid_id)
        self.assertIsInstance(preset, MotionPreset)
        self.assertEqual(preset.id, valid_id)
        self.assertIs(preset, PRESETS[valid_id])

    def test_get_preset_non_existing(self):
        """Test get_preset raises KeyError for an invalid ID."""
        with self.assertRaises(KeyError) as context:
            get_preset("non_existent_preset_id_123")

        self.assertIn("Unknown motion preset 'non_existent_preset_id_123'", str(context.exception))
        self.assertIn("Available:", str(context.exception))

    def test_list_presets(self):
        """Test list_presets returns all presets as a list."""
        presets_list = list_presets()
        self.assertIsInstance(presets_list, list)
        self.assertEqual(len(presets_list), len(PRESETS))

        for preset in presets_list:
            self.assertIsInstance(preset, MotionPreset)
            self.assertIn(preset.id, PRESETS)
            self.assertIs(preset, PRESETS[preset.id])

if __name__ == "__main__":
    unittest.main()

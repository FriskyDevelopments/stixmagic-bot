"""
Tests for pipeline/motion_presets/catalog.py - Motion preset catalog.
"""

import unittest

from pipeline.motion_presets.catalog import PRESETS, get_preset, list_presets
from pipeline.motion_presets.preset import MotionPreset


class TestMotionPresetsCatalog(unittest.TestCase):

    def test_presets_dict_contains_expected_presets(self):
        """Test that PRESETS dict contains all built-in presets."""
        self.assertIsInstance(PRESETS, dict)
        self.assertGreaterEqual(len(PRESETS), 10)

        expected_ids = [
            "pulse",
            "glow",
            "wobble",
            "bounce",
            "orbit",
            "glitch",
            "sparkle",
            "particle_burst",
            "laser_sweep",
            "signal_flash",
        ]

        for expected_id in expected_ids:
            self.assertIn(expected_id, PRESETS)
            preset = PRESETS[expected_id]
            self.assertIsInstance(preset, MotionPreset)
            self.assertEqual(preset.id, expected_id)

    def test_get_preset_success(self):
        """Test getting a valid preset by ID."""
        preset = get_preset("pulse")
        self.assertIsInstance(preset, MotionPreset)
        self.assertEqual(preset.id, "pulse")

    def test_get_preset_key_error(self):
        """Test getting an invalid preset raises KeyError."""
        with self.assertRaises(KeyError) as context:
            get_preset("non_existent_preset_id_123")

        self.assertIn(
            "Unknown motion preset 'non_existent_preset_id_123'", str(context.exception)
        )

    def test_list_presets(self):
        """Test listing all presets returns a list of MotionPreset objects."""
        presets_list = list_presets()
        self.assertIsInstance(presets_list, list)
        self.assertEqual(len(presets_list), len(PRESETS))

        for preset in presets_list:
            self.assertIsInstance(preset, MotionPreset)

    def test_list_presets_matches_dict_values(self):
        """Test list_presets() returns the same instances as PRESETS.values()."""
        presets_list = list_presets()
        presets_values = list(PRESETS.values())

        self.assertEqual(presets_list, presets_values)


if __name__ == "__main__":
    unittest.main()

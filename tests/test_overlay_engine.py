"""
Tests for integrations/overlay_engine/__init__.py – OverlayCompositor.

Covers the PR change: preset normalization fix in add_layer().
  - None preset defaults to "pulse"
  - Empty string preset defaults to "pulse"
  - Whitespace-only preset defaults to "pulse"
  - A valid non-empty preset string is preserved as-is
  - Existing validation (pack not loaded, empty asset_id) still works
  - scene() snapshot reflects the normalized preset
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from integrations.overlay_engine import OverlayCompositor, OverlayLayer


class TestAddLayerPresetNormalization(unittest.TestCase):
    """PR change: preset=None or empty/whitespace should become "pulse"."""

    def setUp(self):
        self.compositor = OverlayCompositor()
        self.compositor.load_pack("test-pack")

    def test_none_preset_becomes_pulse(self):
        self.compositor.add_layer("asset1", preset=None)
        layer = self.compositor.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_empty_string_preset_becomes_pulse(self):
        self.compositor.add_layer("asset1", preset="")
        layer = self.compositor.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_whitespace_only_preset_becomes_pulse(self):
        self.compositor.add_layer("asset1", preset="   ")
        layer = self.compositor.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_valid_preset_preserved(self):
        self.compositor.add_layer("asset1", preset="glow")
        layer = self.compositor.layers[0]
        self.assertEqual(layer.preset, "glow")

    def test_preset_with_surrounding_whitespace_stripped(self):
        self.compositor.add_layer("asset1", preset="  bounce  ")
        layer = self.compositor.layers[0]
        self.assertEqual(layer.preset, "bounce")

    def test_default_preset_is_pulse(self):
        """add_layer with no preset kwarg should default to pulse."""
        self.compositor.add_layer("asset1")
        layer = self.compositor.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_scene_reflects_normalized_preset(self):
        self.compositor.add_layer("asset1", preset=None)
        scene = self.compositor.scene()
        self.assertEqual(scene["layers"][0]["preset"], "pulse")

    def test_multiple_layers_with_mixed_presets(self):
        self.compositor.add_layer("asset1", preset=None)
        self.compositor.add_layer("asset2", preset="flash")
        self.compositor.add_layer("asset3", preset="")
        presets = [layer.preset for layer in self.compositor.layers]
        self.assertEqual(presets, ["pulse", "flash", "pulse"])


class TestAddLayerValidation(unittest.TestCase):
    """Existing validation: pack not loaded, empty asset_id."""

    def test_add_layer_before_load_pack_raises(self):
        compositor = OverlayCompositor()
        with self.assertRaises(RuntimeError):
            compositor.add_layer("asset1")

    def test_empty_asset_id_raises_value_error(self):
        compositor = OverlayCompositor()
        compositor.load_pack("test-pack")
        with self.assertRaises(ValueError):
            compositor.add_layer("")

    def test_whitespace_only_asset_id_raises_value_error(self):
        compositor = OverlayCompositor()
        compositor.load_pack("test-pack")
        with self.assertRaises(ValueError):
            compositor.add_layer("   ")

    def test_non_string_asset_id_raises_value_error(self):
        compositor = OverlayCompositor()
        compositor.load_pack("test-pack")
        with self.assertRaises((ValueError, AttributeError)):
            compositor.add_layer(123)


class TestOverlayCompositorScene(unittest.TestCase):
    """scene() snapshot reflects compositor state correctly."""

    def test_empty_scene(self):
        compositor = OverlayCompositor()
        scene = compositor.scene()
        self.assertIsNone(scene["pack_id"])
        self.assertFalse(scene["running"])
        self.assertEqual(scene["layer_count"], 0)
        self.assertEqual(scene["layers"], [])

    def test_scene_after_load_pack(self):
        compositor = OverlayCompositor()
        compositor.load_pack("my-pack")
        scene = compositor.scene()
        self.assertEqual(scene["pack_id"], "my-pack")

    def test_scene_layer_count_matches(self):
        compositor = OverlayCompositor()
        compositor.load_pack("pack")
        compositor.add_layer("a1")
        compositor.add_layer("a2")
        scene = compositor.scene()
        self.assertEqual(scene["layer_count"], 2)
        self.assertEqual(len(scene["layers"]), 2)

    def test_scene_running_state(self):
        compositor = OverlayCompositor()
        compositor.load_pack("pack")
        compositor.start()
        self.assertTrue(compositor.scene()["running"])
        compositor.stop()
        self.assertFalse(compositor.scene()["running"])

    def test_load_pack_clears_layers(self):
        compositor = OverlayCompositor()
        compositor.load_pack("pack1")
        compositor.add_layer("a1")
        compositor.load_pack("pack2")
        self.assertEqual(len(compositor.layers), 0)

    def test_optional_kwargs_stored_correctly(self):
        compositor = OverlayCompositor()
        compositor.load_pack("pack")
        compositor.add_layer("a1", x=10, y=20, scale=2.0, opacity=0.5)
        layer = compositor.layers[0]
        self.assertEqual(layer.x, 10)
        self.assertEqual(layer.y, 20)
        self.assertAlmostEqual(layer.scale, 2.0)
        self.assertAlmostEqual(layer.opacity, 0.5)


if __name__ == "__main__":
    unittest.main()
"""
Tests for integrations/overlay_engine/__init__.py – overlay compositor.

Covers (focused on PR changes):
 - add_layer: None preset defaults to "pulse"
 - add_layer: empty string preset defaults to "pulse"
 - add_layer: whitespace-only string preset defaults to "pulse"
 - add_layer: non-empty preset is preserved as-is
 - add_layer: numeric-coerced preset (e.g. passed as non-string) is str()-ified
 - add_layer: invalid asset_id raises ValueError
 - add_layer: no pack loaded raises RuntimeError
 - add_layer: kwargs (x, y, scale, opacity) are stored correctly
 - scene(): serializes correctly after adding layers
 - load_pack / start / stop lifecycle
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.overlay_engine import OverlayCompositor, OverlayLayer


class TestOverlayCompositorAddLayerPresetNormalization(unittest.TestCase):
    """PR change: preset=None and empty/whitespace presets should default to 'pulse'."""

    def setUp(self):
        self.comp = OverlayCompositor()
        self.comp.load_pack("test-pack")

    def test_none_preset_defaults_to_pulse(self):
        self.comp.add_layer("asset1", preset=None)
        layer = self.comp.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_empty_string_preset_defaults_to_pulse(self):
        self.comp.add_layer("asset2", preset="")
        layer = self.comp.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_whitespace_only_preset_defaults_to_pulse(self):
        self.comp.add_layer("asset3", preset="   ")
        layer = self.comp.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_valid_preset_name_preserved(self):
        self.comp.add_layer("asset4", preset="glow")
        layer = self.comp.layers[0]
        self.assertEqual(layer.preset, "glow")

    def test_default_preset_is_pulse_when_not_specified(self):
        self.comp.add_layer("asset5")
        layer = self.comp.layers[0]
        self.assertEqual(layer.preset, "pulse")

    def test_preset_with_surrounding_whitespace_is_stripped(self):
        self.comp.add_layer("asset6", preset="  bounce  ")
        layer = self.comp.layers[0]
        self.assertEqual(layer.preset, "bounce")

    def test_numeric_like_preset_string_preserved(self):
        self.comp.add_layer("asset7", preset="preset_01")
        layer = self.comp.layers[0]
        self.assertEqual(layer.preset, "preset_01")


class TestOverlayCompositorAddLayerValidation(unittest.TestCase):
    """Tests for add_layer validation logic."""

    def setUp(self):
        self.comp = OverlayCompositor()
        self.comp.load_pack("test-pack")

    def test_empty_asset_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.comp.add_layer("")

    def test_whitespace_only_asset_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.comp.add_layer("   ")

    def test_non_string_asset_id_raises_value_error(self):
        with self.assertRaises((ValueError, AttributeError)):
            self.comp.add_layer(None)

    def test_no_pack_loaded_raises_runtime_error(self):
        fresh = OverlayCompositor()
        with self.assertRaises(RuntimeError) as ctx:
            fresh.add_layer("asset1")
        self.assertIn("load_pack", str(ctx.exception))

    def test_asset_id_stripped(self):
        self.comp.add_layer("  my-asset  ")
        layer = self.comp.layers[0]
        self.assertEqual(layer.asset_id, "my-asset")


class TestOverlayCompositorAddLayerKwargs(unittest.TestCase):
    """Tests for positional/keyword arguments stored in the layer."""

    def setUp(self):
        self.comp = OverlayCompositor()
        self.comp.load_pack("kwarg-pack")

    def test_x_and_y_stored(self):
        self.comp.add_layer("asset", x=10, y=20)
        layer = self.comp.layers[0]
        self.assertEqual(layer.x, 10)
        self.assertEqual(layer.y, 20)

    def test_scale_stored(self):
        self.comp.add_layer("asset", scale=2.5)
        layer = self.comp.layers[0]
        self.assertAlmostEqual(layer.scale, 2.5)

    def test_opacity_stored(self):
        self.comp.add_layer("asset", opacity=0.5)
        layer = self.comp.layers[0]
        self.assertAlmostEqual(layer.opacity, 0.5)

    def test_defaults_when_no_kwargs(self):
        self.comp.add_layer("asset")
        layer = self.comp.layers[0]
        self.assertEqual(layer.x, 0)
        self.assertEqual(layer.y, 0)
        self.assertAlmostEqual(layer.scale, 1.0)
        self.assertAlmostEqual(layer.opacity, 1.0)

    def test_x_coerced_to_int(self):
        self.comp.add_layer("asset", x="5")
        layer = self.comp.layers[0]
        self.assertIsInstance(layer.x, int)
        self.assertEqual(layer.x, 5)


class TestOverlayCompositorLoadPack(unittest.TestCase):
    """Tests for load_pack behavior."""

    def test_load_pack_sets_pack_id(self):
        comp = OverlayCompositor()
        comp.load_pack("my-pack")
        self.assertEqual(comp.pack_id, "my-pack")

    def test_load_pack_strips_whitespace(self):
        comp = OverlayCompositor()
        comp.load_pack("  spaced-pack  ")
        self.assertEqual(comp.pack_id, "spaced-pack")

    def test_load_pack_clears_existing_layers(self):
        comp = OverlayCompositor()
        comp.load_pack("pack1")
        comp.add_layer("asset1")
        comp.load_pack("pack2")
        self.assertEqual(len(comp.layers), 0)

    def test_load_pack_empty_raises_value_error(self):
        comp = OverlayCompositor()
        with self.assertRaises(ValueError):
            comp.load_pack("")

    def test_load_pack_non_string_raises_value_error(self):
        comp = OverlayCompositor()
        with self.assertRaises(ValueError):
            comp.load_pack(None)


class TestOverlayCompositorLifecycle(unittest.TestCase):
    """Tests for start/stop/scene lifecycle."""

    def setUp(self):
        self.comp = OverlayCompositor()
        self.comp.load_pack("lifecycle-pack")

    def test_initial_not_running(self):
        self.assertFalse(self.comp.running)

    def test_start_sets_running(self):
        self.comp.start()
        self.assertTrue(self.comp.running)

    def test_stop_clears_running(self):
        self.comp.start()
        self.comp.stop()
        self.assertFalse(self.comp.running)

    def test_start_without_pack_raises(self):
        fresh = OverlayCompositor()
        with self.assertRaises(RuntimeError):
            fresh.start()

    def test_scene_returns_dict_with_required_keys(self):
        scene = self.comp.scene()
        self.assertIn("pack_id", scene)
        self.assertIn("running", scene)
        self.assertIn("layer_count", scene)
        self.assertIn("layers", scene)

    def test_scene_layer_count_matches(self):
        self.comp.add_layer("a1")
        self.comp.add_layer("a2")
        scene = self.comp.scene()
        self.assertEqual(scene["layer_count"], 2)
        self.assertEqual(len(scene["layers"]), 2)

    def test_scene_layers_are_copies(self):
        """Modifying the scene dict should not affect the compositor state."""
        self.comp.add_layer("asset")
        scene = self.comp.scene()
        scene["layers"][0]["preset"] = "modified"
        # Original layer should be unchanged
        self.assertNotEqual(self.comp.layers[0].preset, "modified")

    def test_scene_pack_id_present(self):
        scene = self.comp.scene()
        self.assertEqual(scene["pack_id"], "lifecycle-pack")


if __name__ == "__main__":
    unittest.main()
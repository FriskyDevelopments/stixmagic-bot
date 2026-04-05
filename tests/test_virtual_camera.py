"""
Tests for integrations/virtual_camera/__init__.py – virtual camera adapter.

Covers (focused on PR changes):
 - __init__: fps type validation (must be int or float)
 - __init__: fps value validation (must be > 0)
 - __init__: resolution must contain exactly two values
 - __init__: resolution values must be numeric (int or float)
 - __init__: resolution values must be > 0
 - __init__: non-iterable resolution raises ValueError
 - push_frame: works when running
 - push_frame: raises RuntimeError when not started
 - push_frame: raises ValueError for None frame
 - start / stop / running property
 - last_frame property
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.virtual_camera import VirtualCamera


class TestVirtualCameraFpsValidation(unittest.TestCase):
    """PR change: fps must be a numeric type (int or float), not just > 0."""

    def test_int_fps_accepted(self):
        cam = VirtualCamera(fps=30)
        self.assertEqual(cam.fps, 30)

    def test_float_fps_accepted(self):
        cam = VirtualCamera(fps=29.97)
        self.assertAlmostEqual(cam.fps, 29.97)

    def test_string_fps_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(fps="30")
        self.assertIn("numeric", str(ctx.exception).lower())

    def test_none_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=None)

    def test_list_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=[30])

    def test_zero_fps_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(fps=0)
        self.assertIn("greater than 0", str(ctx.exception))

    def test_negative_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=-1)

    def test_negative_float_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=-0.1)

    def test_boundary_small_positive_float_accepted(self):
        cam = VirtualCamera(fps=0.001)
        self.assertGreater(cam.fps, 0)


class TestVirtualCameraResolutionValidation(unittest.TestCase):
    """PR change: resolution validation now checks len, types, and values."""

    def test_default_resolution_accepted(self):
        cam = VirtualCamera()
        self.assertEqual(cam.resolution, (1280, 720))

    def test_custom_valid_resolution(self):
        cam = VirtualCamera(resolution=(1920, 1080))
        self.assertEqual(cam.resolution, (1920, 1080))

    def test_float_resolution_accepted(self):
        cam = VirtualCamera(resolution=(640.0, 480.0))
        self.assertEqual(cam.resolution[0], 640.0)

    def test_single_element_resolution_raises(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(resolution=(1280,))
        self.assertIn("two", str(ctx.exception).lower())

    def test_three_element_resolution_raises(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(resolution=(1280, 720, 3))
        self.assertIn("two", str(ctx.exception).lower())

    def test_empty_resolution_raises(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=())

    def test_string_width_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(resolution=("1280", 720))
        self.assertIn("numeric", str(ctx.exception).lower())

    def test_string_height_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(resolution=(1280, "720"))
        self.assertIn("numeric", str(ctx.exception).lower())

    def test_zero_width_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(resolution=(0, 720))
        self.assertIn("greater than 0", str(ctx.exception))

    def test_zero_height_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(resolution=(1280, 0))
        self.assertIn("greater than 0", str(ctx.exception))

    def test_negative_width_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(-100, 720))

    def test_negative_height_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(1280, -100))

    def test_non_iterable_resolution_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            VirtualCamera(resolution=1280)
        self.assertIn("sequence", str(ctx.exception).lower())

    def test_none_resolution_raises_value_error(self):
        with self.assertRaises((ValueError, TypeError)):
            VirtualCamera(resolution=None)

    def test_list_resolution_accepted(self):
        """Lists should also work as resolution since len() and unpacking work."""
        cam = VirtualCamera(resolution=[1280, 720])
        self.assertEqual(cam.resolution[0], 1280)
        self.assertEqual(cam.resolution[1], 720)


class TestVirtualCameraInitState(unittest.TestCase):
    """Tests for initial state after construction."""

    def test_initial_running_is_false(self):
        cam = VirtualCamera()
        self.assertFalse(cam.running)

    def test_initial_last_frame_is_none(self):
        cam = VirtualCamera()
        self.assertIsNone(cam.last_frame)

    def test_device_stored(self):
        cam = VirtualCamera(device="/dev/video1")
        self.assertEqual(cam.device, "/dev/video1")

    def test_default_device(self):
        cam = VirtualCamera()
        self.assertEqual(cam.device, "/dev/video0")


class TestVirtualCameraLifecycle(unittest.TestCase):
    """Tests for start/stop/push_frame behavior."""

    def test_start_sets_running_true(self):
        cam = VirtualCamera()
        cam.start()
        self.assertTrue(cam.running)

    def test_stop_sets_running_false(self):
        cam = VirtualCamera()
        cam.start()
        cam.stop()
        self.assertFalse(cam.running)

    def test_push_frame_when_running(self):
        cam = VirtualCamera()
        cam.start()
        cam.push_frame("frame_data")
        self.assertEqual(cam.last_frame, "frame_data")

    def test_push_frame_when_not_running_raises(self):
        cam = VirtualCamera()
        with self.assertRaises(RuntimeError) as ctx:
            cam.push_frame("frame")
        self.assertIn("start", str(ctx.exception).lower())

    def test_push_frame_none_raises_value_error(self):
        cam = VirtualCamera()
        cam.start()
        with self.assertRaises(ValueError):
            cam.push_frame(None)

    def test_push_frame_updates_last_frame(self):
        cam = VirtualCamera()
        cam.start()
        cam.push_frame("first")
        cam.push_frame("second")
        self.assertEqual(cam.last_frame, "second")

    def test_stop_then_push_raises(self):
        cam = VirtualCamera()
        cam.start()
        cam.stop()
        with self.assertRaises(RuntimeError):
            cam.push_frame("frame")

    def test_restart_allows_push(self):
        cam = VirtualCamera()
        cam.start()
        cam.stop()
        cam.start()
        cam.push_frame("after-restart")
        self.assertEqual(cam.last_frame, "after-restart")


if __name__ == "__main__":
    unittest.main()
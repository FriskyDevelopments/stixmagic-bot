"""
Tests for integrations/virtual_camera/__init__.py – VirtualCamera.

Covers the PR changes: enhanced __init__ validation.
  - fps: must be numeric (int or float), must be > 0
  - resolution: must be a sequence of exactly 2 items, both numeric, both > 0
  - TypeError on non-iterable resolution
  - Existing push_frame / start / stop behavior
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from integrations.virtual_camera import VirtualCamera


class TestVirtualCameraFpsValidation(unittest.TestCase):
    """PR change: fps must be numeric type and > 0."""

    def test_valid_int_fps(self):
        cam = VirtualCamera(fps=30)
        self.assertEqual(cam.fps, 30)

    def test_valid_float_fps(self):
        cam = VirtualCamera(fps=29.97)
        self.assertAlmostEqual(cam.fps, 29.97)

    def test_fps_of_one_is_valid(self):
        cam = VirtualCamera(fps=1)
        self.assertEqual(cam.fps, 1)

    def test_zero_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=0)

    def test_negative_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=-1)

    def test_string_fps_raises_value_error(self):
        """PR change: string fps must raise ValueError (not TypeError)."""
        with self.assertRaises(ValueError):
            VirtualCamera(fps="30")

    def test_none_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=None)

    def test_list_fps_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(fps=[30])

    def test_fps_error_message_mentions_numeric(self):
        try:
            VirtualCamera(fps="fast")
        except ValueError as e:
            self.assertIn("numeric", str(e).lower())

    def test_fps_zero_error_message_mentions_greater_than_zero(self):
        try:
            VirtualCamera(fps=0)
        except ValueError as e:
            self.assertIn("0", str(e))


class TestVirtualCameraResolutionValidation(unittest.TestCase):
    """PR change: enhanced resolution validation."""

    def test_valid_resolution_tuple(self):
        cam = VirtualCamera(resolution=(1280, 720))
        self.assertEqual(cam.resolution, (1280, 720))

    def test_valid_resolution_list(self):
        cam = VirtualCamera(resolution=[640, 480])
        self.assertIsNotNone(cam)

    def test_valid_float_resolution(self):
        cam = VirtualCamera(resolution=(1920.0, 1080.0))
        self.assertIsNotNone(cam)

    def test_zero_width_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(0, 720))

    def test_zero_height_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(1280, 0))

    def test_negative_width_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(-1, 720))

    def test_negative_height_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(1280, -1))

    def test_single_element_resolution_raises_value_error(self):
        """PR change: resolution must have exactly 2 values."""
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(1280,))

    def test_three_element_resolution_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(1280, 720, 3))

    def test_string_width_raises_value_error(self):
        """PR change: resolution values must be numeric."""
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=("1280", 720))

    def test_string_height_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=(1280, "720"))

    def test_none_resolution_raises_value_error(self):
        """PR change: non-iterable resolution raises ValueError."""
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=None)

    def test_integer_resolution_raises_value_error(self):
        """PR change: integer (non-iterable) resolution raises ValueError."""
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=1280)

    def test_empty_resolution_raises_value_error(self):
        with self.assertRaises(ValueError):
            VirtualCamera(resolution=())


class TestVirtualCameraLifecycle(unittest.TestCase):
    """Existing lifecycle behavior: start, push_frame, stop."""

    def test_initial_state_not_running(self):
        cam = VirtualCamera()
        self.assertFalse(cam.running)

    def test_initial_last_frame_none(self):
        cam = VirtualCamera()
        self.assertIsNone(cam.last_frame)

    def test_start_sets_running_true(self):
        cam = VirtualCamera()
        cam.start()
        self.assertTrue(cam.running)

    def test_stop_sets_running_false(self):
        cam = VirtualCamera()
        cam.start()
        cam.stop()
        self.assertFalse(cam.running)

    def test_push_frame_before_start_raises(self):
        cam = VirtualCamera()
        with self.assertRaises(RuntimeError):
            cam.push_frame(b"frame-data")

    def test_push_frame_none_raises_value_error(self):
        cam = VirtualCamera()
        cam.start()
        with self.assertRaises(ValueError):
            cam.push_frame(None)

    def test_push_frame_stores_frame(self):
        cam = VirtualCamera()
        cam.start()
        frame = b"frame-bytes"
        cam.push_frame(frame)
        self.assertEqual(cam.last_frame, frame)

    def test_push_frame_after_stop_raises(self):
        cam = VirtualCamera()
        cam.start()
        cam.stop()
        with self.assertRaises(RuntimeError):
            cam.push_frame(b"data")

    def test_device_stored(self):
        cam = VirtualCamera(device="/dev/video1")
        self.assertEqual(cam.device, "/dev/video1")

    def test_default_device(self):
        cam = VirtualCamera()
        self.assertEqual(cam.device, "/dev/video0")


if __name__ == "__main__":
    unittest.main()
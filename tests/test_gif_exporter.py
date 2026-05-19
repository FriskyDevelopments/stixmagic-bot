import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pipeline.asset_model.asset import Asset
from pipeline.motion_presets.preset import MotionPreset
from pipeline.exporters.gif_exporter import GifExporter


class TestGifExporter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.exporter = GifExporter(renders_dir=self.temp_dir)
        self.asset = Asset(
            id="test_asset",
            name="Test Asset",
            category="letter",
            theme="neon",
            source_format="png",
            source_path="test.png",
            width=100,
            height=100,
        )
        self.preset = MotionPreset(
            id="test_preset",
            name="Test Preset",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_success(self):
        result = self.exporter.export(self.asset, self.preset)

        self.assertTrue(result.success)
        self.assertEqual(result.format, "gif")
        self.assertIsNotNone(result.path)
        self.assertTrue(os.path.exists(result.path))
        self.assertTrue(result.path.startswith(self.temp_dir))
        self.assertTrue(result.path.endswith("test_asset_test_preset.gif"))

        with open(result.path, "rb") as f:
            content = f.read()
            self.assertTrue(content.startswith(b"GIF89a"))

    @patch("pipeline.exporters.gif_exporter.GifExporter._render_frames")
    def test_export_exception_handled(self, mock_render_frames):
        mock_render_frames.side_effect = Exception("Rendering failed")

        result = self.exporter.export(self.asset, self.preset)

        self.assertFalse(result.success)
        self.assertEqual(result.format, "gif")
        self.assertEqual(result.message, "Rendering failed")

        expected_path = self.exporter.output_path(self.asset, self.preset)
        self.assertFalse(os.path.exists(expected_path))


if __name__ == "__main__":
    unittest.main()

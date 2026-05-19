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
            height=100
        )
        self.preset = MotionPreset(
            id="test_preset",
            name="Test Preset"
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_success(self):
        result = self.exporter.export(self.asset, self.preset)

        self.assertTrue(result.success)
        self.assertEqual(result.format, "gif")
        expected_filename = f"{self.asset.id}_{self.preset.id}.gif"
        self.assertTrue(result.path.endswith(expected_filename))
        self.assertTrue(os.path.exists(result.path))

        with open(result.path, "rb") as fh:
            data = fh.read()

        expected_bytes = self.exporter._render_frames(self.asset, self.preset)
        self.assertEqual(data, expected_bytes)
        self.assertEqual(result.size_bytes, len(expected_bytes))

    def test_export_failure(self):
        with patch.object(self.exporter, '_render_frames', side_effect=Exception("Test Error")):
            result = self.exporter.export(self.asset, self.preset)

            self.assertFalse(result.success)
            self.assertEqual(result.format, "gif")
            self.assertIn("Test Error", result.message)

    def test_render_frames_returns_minimal_gif(self):
        frames = self.exporter._render_frames(self.asset, self.preset)
        self.assertTrue(frames.startswith(b"GIF89a"))
        self.assertTrue(frames.endswith(b";"))

if __name__ == '__main__':
    unittest.main()

import unittest
from pipeline.exporters import ExportResult

class TestExportResult(unittest.TestCase):
    def test_summary_all_ok(self):
        result = ExportResult(
            asset_id="test_asset",
            preset_id="test_preset",
            gif="test.gif",
            webp="test.webp",
            webm="test.webm",
            mov="test.mov",
            png_sequence_dir="test_dir",
            thumbnail="test_thumb.png"
        )
        self.assertEqual(result.summary, "OK (gif,webp,webm,mov,png_seq,thumb)")

    def test_summary_failed(self):
        result = ExportResult(
            asset_id="test_asset",
            preset_id="test_preset",
        )
        self.assertEqual(result.summary, "FAILED")

    def test_summary_with_errors(self):
        result = ExportResult(
            asset_id="test_asset",
            preset_id="test_preset",
            gif="test.gif"
        )
        result.errors.append("error 1")
        result.errors.append("error 2")
        self.assertEqual(result.summary, "OK (gif) with 2 error(s)")

    def test_summary_failed_with_errors(self):
        result = ExportResult(
            asset_id="test_asset",
            preset_id="test_preset",
        )
        result.errors.append("error 1")
        self.assertEqual(result.summary, "FAILED with 1 error(s)")

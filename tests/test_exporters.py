import os
import tempfile
import unittest
from unittest.mock import patch

import pipeline.exporters as exporters
from pipeline.motion_presets import MotionPreset


class TestExportAllCustomFormats(unittest.TestCase):

    def test_successful_format_without_declared_attribute_is_preserved(self):
        preset = MotionPreset(id="spin", name="Spin")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "custom.out")

            def export_custom(source_path, preset, output_dir):
                os.makedirs(output_dir, exist_ok=True)
                return output_path

            dispatch = {"custom_format": (export_custom, tmpdir)}

            with patch.object(exporters, "_get_dispatch", return_value=dispatch):
                result = exporters.export_all(
                    "asset1",
                    "asset1.png",
                    preset,
                    renders_root=tmpdir,
                    formats=["custom_format"],
                )

        self.assertEqual(result.errors, [])
        self.assertTrue(hasattr(result, "custom_format"))
        self.assertEqual(result.custom_format, output_path)

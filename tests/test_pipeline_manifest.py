import json
import os
import tempfile
import unittest
from unittest.mock import patch

from pipeline.manifest import generate_pipeline_manifest
from pipeline.packager import PackManifest, PackManifestEntry


class TestPipelineManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.packs_dir = os.path.join(self.temp_dir.name, "packs")
        os.makedirs(self.packs_dir)

        self.output_path = os.path.join(self.temp_dir.name, "pipeline_manifest.json")
        self.catalog_path = os.path.join(self.temp_dir.name, "catalog.json")

        # Create a dummy catalog
        dummy_catalog = [
            {
                "id": "asset1",
                "name": "Asset One",
                "category": "letter",
                "source_format": "png",
                "source_path": "src/asset1.png",
                "export_targets": ["gif"]
            }
        ]
        with open(self.catalog_path, "w") as f:
            json.dump(dummy_catalog, f)

    def test_missing_packs_dir(self):
        """Test with a packs_dir that doesn't exist."""
        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=os.path.join(self.temp_dir.name, "nonexistent"),
            catalog_path=self.catalog_path
        )
        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(result["packs"], [])

        # Verify file was written
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path) as f:
            data = json.load(f)
            self.assertEqual(data["total_packs"], 0)

    @patch("pipeline.packager.build_pack")
    def test_successful_manifest_generation(self, mock_build_pack):
        """Test successful generation with valid packs."""
        # Setup fake pack directory and file
        pack_dir = os.path.join(self.packs_dir, "test_pack")
        os.makedirs(pack_dir)

        pack_json = {
            "pack_id": "test_pack",
            "title": "Test Pack",
            "included_assets": ["asset1"]
        }
        with open(os.path.join(pack_dir, "pack.json"), "w") as f:
            json.dump(pack_json, f)

        # Mock build_pack
        mock_manifest = PackManifest(
            pack_id="test_pack",
            entries=[
                PackManifestEntry(
                    asset_id="asset1",
                    preset_id="preset1",
                    expected_outputs={
                        "gif": "renders/gif/asset1_preset1.gif",
                        "thumbnail": "renders/thumbnails/asset1_thumb.png"
                    }
                )
            ]
        )
        mock_build_pack.return_value = mock_manifest

        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            catalog_path=self.catalog_path
        )

        self.assertEqual(result["total_packs"], 1)
        self.assertEqual(result["total_assets"], 1)
        self.assertEqual(len(result["packs"]), 1)

        pack_data = result["packs"][0]
        self.assertEqual(pack_data["pack_id"], "test_pack")
        self.assertEqual(len(pack_data["entries"]), 1)

        entry = pack_data["entries"][0]
        self.assertEqual(entry["asset_id"], "asset1")
        self.assertEqual(entry["thumbnail"], "renders/thumbnails/asset1_thumb.png")
        self.assertEqual(entry["outputs"]["gif"], "renders/gif/asset1_preset1.gif")

        # Verify file was written correctly
        with open(self.output_path) as f:
            written_data = json.load(f)
            self.assertEqual(written_data["total_packs"], 1)

    def test_invalid_pack_json(self):
        """Test handling of an invalid pack.json file."""
        pack_dir = os.path.join(self.packs_dir, "bad_pack")
        os.makedirs(pack_dir)

        # Write invalid JSON
        with open(os.path.join(pack_dir, "pack.json"), "w") as f:
            f.write("{ invalid json")

        # Write a valid JSON for another pack
        good_pack_dir = os.path.join(self.packs_dir, "good_pack")
        os.makedirs(good_pack_dir)
        with open(os.path.join(good_pack_dir, "pack.json"), "w") as f:
            json.dump({
                "pack_id": "good_pack",
                "title": "Good Pack",
                "included_assets": []
            }, f)

        with patch("pipeline.packager.build_pack") as mock_build_pack:
            mock_build_pack.return_value = PackManifest(pack_id="good_pack", entries=[])

            with patch("pipeline.manifest.logger") as mock_logger:
                result = generate_pipeline_manifest(
                    output_path=self.output_path,
                    packs_dir=self.packs_dir,
                    catalog_path=self.catalog_path
                )

                # Should have 1 pack (the good one), the bad one should be skipped
                self.assertEqual(result["total_packs"], 1)

                # Verify logger.error was called for the bad pack
                mock_logger.error.assert_any_call("Skipping %s – failed to load: %s", os.path.join(pack_dir, "pack.json"), unittest.mock.ANY)

    @patch("pipeline.packager.build_pack")
    def test_build_pack_failure(self, mock_build_pack):
        """Test handling when build_pack raises an exception."""
        pack_dir = os.path.join(self.packs_dir, "fail_pack")
        os.makedirs(pack_dir)
        with open(os.path.join(pack_dir, "pack.json"), "w") as f:
            json.dump({
                "pack_id": "fail_pack",
                "title": "Fail Pack",
            }, f)

        mock_build_pack.side_effect = Exception("Simulated build_pack error")

        with patch("pipeline.manifest.logger") as mock_logger:
            result = generate_pipeline_manifest(
                output_path=self.output_path,
                packs_dir=self.packs_dir,
                catalog_path=self.catalog_path
            )

            # Pack should be skipped
            self.assertEqual(result["total_packs"], 0)
            mock_logger.error.assert_any_call("Skipping pack %r – build_pack failed: %s", "fail_pack", unittest.mock.ANY)

    def test_output_write_failure(self):
        """Test that function handles failure to write the output file."""
        # Create a bad output path (directory doesn't exist)
        bad_output_path = os.path.join(self.temp_dir.name, "does_not_exist", "out.json")

        with patch("pipeline.manifest.logger") as mock_logger:
            result = generate_pipeline_manifest(
                output_path=bad_output_path,
                packs_dir=self.packs_dir,
                catalog_path=self.catalog_path
            )

            # Dictionary should still be returned
            self.assertEqual(result["total_packs"], 0)

            # Logger should record the error
            mock_logger.error.assert_called_with("Failed to write manifest to %s: %s", bad_output_path, unittest.mock.ANY)

if __name__ == "__main__":
    unittest.main()

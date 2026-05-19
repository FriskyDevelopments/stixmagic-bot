import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from pipeline.manifest import generate_pipeline_manifest

class TestPipelineManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.packs_dir = os.path.join(self.temp_dir.name, "packs")
        os.makedirs(self.packs_dir)
        self.output_path = os.path.join(self.temp_dir.name, "output.json")
        self.catalog_path = os.path.join(self.temp_dir.name, "catalog.json")

        # Create a dummy catalog
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "id": "asset1",
                    "name": "Asset 1",
                    "category": "letter",
                    "source_format": "png",
                    "source_path": "foo.png"
                }
            ], f)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("pipeline.packager.build_pack")
    def test_happy_path(self, mock_build_pack):
        # Create a valid pack
        pack1_dir = os.path.join(self.packs_dir, "pack1")
        os.makedirs(pack1_dir)
        with open(os.path.join(pack1_dir, "pack.json"), "w", encoding="utf-8") as f:
            json.dump({
                "pack_id": "pack1",
                "title": "Pack 1",
                "included_assets": ["asset1"]
            }, f)

        # Mock build_pack result
        mock_manifest = MagicMock()
        mock_entry = MagicMock()
        mock_entry.asset_id = "asset1"
        mock_entry.preset_id = "preset1"
        mock_entry.expected_outputs = {"thumbnail": "thumb.png", "gif": "out.gif"}
        mock_manifest.entries = [mock_entry]
        mock_build_pack.return_value = mock_manifest

        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root="renders",
            catalog_path=self.catalog_path
        )

        self.assertEqual(result["total_packs"], 1)
        self.assertEqual(result["total_assets"], 1)
        self.assertEqual(len(result["packs"]), 1)
        self.assertEqual(result["packs"][0]["pack_id"], "pack1")

        # Verify JSON was written
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r", encoding="utf-8") as f:
            written_data = json.load(f)
        self.assertEqual(written_data["total_packs"], 1)
        self.assertEqual(written_data["packs"][0]["entries"][0]["asset_id"], "asset1")

    def test_missing_packs_dir(self):
        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=os.path.join(self.temp_dir.name, "nonexistent"),
            renders_root="renders",
            catalog_path=self.catalog_path
        )
        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)

        # Verify JSON was written with empty lists
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r", encoding="utf-8") as f:
            written_data = json.load(f)
        self.assertEqual(written_data["total_packs"], 0)

    @patch("pipeline.packager.build_pack")
    def test_invalid_pack(self, mock_build_pack):
        # Create an invalid pack (bad json)
        pack_bad_dir = os.path.join(self.packs_dir, "pack_bad")
        os.makedirs(pack_bad_dir)
        with open(os.path.join(pack_bad_dir, "pack.json"), "w", encoding="utf-8") as f:
            f.write("not json")

        # Create a valid pack that fails during build_pack
        pack_fail_dir = os.path.join(self.packs_dir, "pack_fail")
        os.makedirs(pack_fail_dir)
        with open(os.path.join(pack_fail_dir, "pack.json"), "w", encoding="utf-8") as f:
            json.dump({
                "pack_id": "pack_fail",
                "title": "Pack Fail"
            }, f)

        mock_build_pack.side_effect = Exception("Build failed")

        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root="renders",
            catalog_path=self.catalog_path
        )

        # Both packs should be skipped
        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)

    @patch("pipeline.packager.build_pack")
    def test_file_writing_failure(self, mock_build_pack):
        # Create a valid pack
        pack1_dir = os.path.join(self.packs_dir, "pack1")
        os.makedirs(pack1_dir)
        with open(os.path.join(pack1_dir, "pack.json"), "w", encoding="utf-8") as f:
            json.dump({
                "pack_id": "pack1",
                "title": "Pack 1"
            }, f)

        mock_manifest = MagicMock()
        mock_manifest.entries = []
        mock_build_pack.return_value = mock_manifest

        # Use an invalid output path that will cause an OSError when opening for writing
        invalid_output_path = os.path.join(self.temp_dir.name, "nonexistent_dir", "output.json")

        result = generate_pipeline_manifest(
            output_path=invalid_output_path,
            packs_dir=self.packs_dir,
            renders_root="renders",
            catalog_path=self.catalog_path
        )

        # Process should succeed and return manifest dict, even if writing to file failed
        self.assertEqual(result["total_packs"], 1)
        self.assertFalse(os.path.exists(invalid_output_path))

if __name__ == '__main__':
    unittest.main()

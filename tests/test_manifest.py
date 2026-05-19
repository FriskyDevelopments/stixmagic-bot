"""
Tests for pipeline/manifest.py
"""
import unittest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from pipeline.manifest import generate_pipeline_manifest

class TestManifest(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        self.packs_dir = self.base_path / "packs"
        self.packs_dir.mkdir()

        self.renders_root = self.base_path / "renders"
        self.renders_root.mkdir()

        self.output_path = self.base_path / "pipeline_manifest.json"
        self.catalog_path = self.base_path / "catalog.json"

        # Write a basic catalog
        self.catalog_data = [
            {
                "id": "asset1",
                "name": "Asset One",
                "category": "letter",
                "source_format": "svg",
                "source_path": "assets/src/asset1.svg"
            }
        ]
        with open(self.catalog_path, "w") as f:
            json.dump(self.catalog_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_manifest_happy_path(self):
        """Test generating manifest with a valid pack."""
        # Create a valid pack.json
        pack1_dir = self.packs_dir / "pack1"
        pack1_dir.mkdir()
        pack_data = {
            "pack_id": "pack1",
            "title": "Pack One",
            "included_assets": ["asset1"],
            "export_formats": ["gif", "thumbnail"],
            "included_motion_presets": ["pulse"]
        }
        with open(pack1_dir / "pack.json", "w") as f:
            json.dump(pack_data, f)

        # Ensure we have a valid motion preset by mocking build_pack dependencies if necessary,
        # but build_pack resolves preset via get_preset which falls back to BUILTIN_PRESETS
        # Let's see if the builtin preset 'pulse' exists.

        manifest = generate_pipeline_manifest(
            output_path=str(self.output_path),
            packs_dir=str(self.packs_dir),
            renders_root=str(self.renders_root),
            catalog_path=str(self.catalog_path)
        )

        self.assertEqual(manifest["total_packs"], 1)
        self.assertEqual(manifest["total_assets"], 1)
        self.assertEqual(len(manifest["packs"]), 1)
        self.assertEqual(manifest["packs"][0]["pack_id"], "pack1")

        # Verify JSON file was created
        self.assertTrue(self.output_path.exists())
        with open(self.output_path) as f:
            saved_manifest = json.load(f)

        self.assertEqual(saved_manifest["total_packs"], 1)

    def test_generate_manifest_missing_packs_dir(self):
        """Test behavior when packs_dir does not exist."""
        non_existent_packs_dir = self.base_path / "does_not_exist"

        manifest = generate_pipeline_manifest(
            output_path=str(self.output_path),
            packs_dir=str(non_existent_packs_dir),
            renders_root=str(self.renders_root),
            catalog_path=str(self.catalog_path)
        )

        self.assertEqual(manifest["total_packs"], 0)
        self.assertEqual(manifest["total_assets"], 0)
        self.assertEqual(len(manifest["packs"]), 0)

    def test_generate_manifest_invalid_pack_json(self):
        """Test skipping packs with invalid JSON."""
        pack_dir = self.packs_dir / "invalid_pack"
        pack_dir.mkdir()

        # Write invalid JSON
        with open(pack_dir / "pack.json", "w") as f:
            f.write("{ invalid json }")

        manifest = generate_pipeline_manifest(
            output_path=str(self.output_path),
            packs_dir=str(self.packs_dir),
            renders_root=str(self.renders_root),
            catalog_path=str(self.catalog_path)
        )

        self.assertEqual(manifest["total_packs"], 0)

    def test_generate_manifest_build_pack_failure(self):
        """Test skipping packs where build_pack fails due to validation."""
        pack_dir = self.packs_dir / "failing_pack"
        pack_dir.mkdir()

        # Valid JSON but missing required fields or referencing unknown assets/presets
        # `strict_validation=False` is passed to build_pack in generate_pipeline_manifest.
        # Let's mock build_pack to raise an exception.
        pack_data = {
            "pack_id": "pack_fail",
            "title": "Pack Fail"
        }
        with open(pack_dir / "pack.json", "w") as f:
            json.dump(pack_data, f)

        with patch("pipeline.packager.build_pack", side_effect=Exception("mock build error")):
            manifest = generate_pipeline_manifest(
                output_path=str(self.output_path),
                packs_dir=str(self.packs_dir),
                renders_root=str(self.renders_root),
                catalog_path=str(self.catalog_path)
            )

        self.assertEqual(manifest["total_packs"], 0)

    def test_generate_manifest_no_pack_files_but_dir_exists(self):
        """Test when packs_dir exists but has no pack subdirectories."""
        manifest = generate_pipeline_manifest(
            output_path=str(self.output_path),
            packs_dir=str(self.packs_dir),
            renders_root=str(self.renders_root),
            catalog_path=str(self.catalog_path)
        )
        self.assertEqual(manifest["total_packs"], 0)

if __name__ == "__main__":
    unittest.main()

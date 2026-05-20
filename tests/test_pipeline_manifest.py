import unittest
import sys
import tempfile
import os
import json
from unittest.mock import patch, MagicMock

# Patch the necessary modules before importing our test logic
def _make_stub(name):
    mod = MagicMock()
    mod.__name__ = name
    return mod

STUBS = {
    "telegram": _make_stub("telegram"),
    "telegram.ext": _make_stub("telegram.ext"),
    "telegram.error": _make_stub("telegram.error"),
    "PIL": _make_stub("PIL"),
    "PIL.Image": _make_stub("PIL.Image"),
    "PIL.ImageOps": _make_stub("PIL.ImageOps"),
    "dotenv": _make_stub("dotenv"),
}

sys.modules.update(STUBS)

from pipeline.manifest import generate_pipeline_manifest
from pipeline.packager import PackManifest, PackManifestEntry
from pipeline.asset_model import Asset, AssetCategory, SourceFormat

class TestPipelineManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.packs_dir = os.path.join(self.temp_dir.name, "packs")
        os.makedirs(self.packs_dir)
        self.output_path = os.path.join(self.temp_dir.name, "manifest.json")
        self.renders_root = os.path.join(self.temp_dir.name, "renders")

        # Basic asset for mocking
        self.dummy_asset = Asset(
            id="letter_A",
            name="Letter A",
            category=AssetCategory.LETTER,
            source_format=SourceFormat.PNG,
            source_path="assets/source/letters/A.png"
        )

        # Patch AssetCatalog where it's imported (in pipeline.metadata)
        self.patcher = patch("pipeline.metadata.AssetCatalog")
        self.mock_catalog_cls = self.patcher.start()
        self.mock_catalog = MagicMock()
        self.mock_catalog_cls.return_value = self.mock_catalog

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_generate_pipeline_manifest_empty(self):
        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
            catalog_path="dummy_catalog.json"
        )
        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(result["packs"], [])

        with open(self.output_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["total_packs"], 0)

    @patch("pipeline.packager.PackDefinition.from_file")
    @patch("pipeline.packager.build_pack")
    def test_generate_pipeline_manifest_success(self, mock_build_pack, mock_from_file):
        # Create a dummy pack file so the discovery finds it
        pack1_dir = os.path.join(self.packs_dir, "pack1")
        os.makedirs(pack1_dir)
        with open(os.path.join(pack1_dir, "pack.json"), "w") as f:
            json.dump({}, f)

        # Mock PackDefinition
        mock_pack = MagicMock()
        mock_pack.pack_id = "test_pack"
        mock_pack.title = "Test Pack"
        mock_pack.theme = "neon"
        mock_pack.target_platforms = ["web"]
        mock_pack.export_formats = ["gif", "thumbnail"]
        mock_from_file.return_value = mock_pack

        # Mock PackManifest
        mock_manifest_entry = PackManifestEntry(
            asset_id="letter_A",
            preset_id="pulse",
            expected_outputs={
                "gif": "renders/gif/letter_A_pulse.gif",
                "thumbnail": "renders/thumbnails/letter_A_thumb.png"
            }
        )
        mock_pack_manifest = PackManifest(
            pack_id="test_pack",
            entries=[mock_manifest_entry]
        )
        mock_build_pack.return_value = mock_pack_manifest

        # Mock catalog
        self.mock_catalog.get.return_value = self.dummy_asset

        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
        )

        self.assertEqual(result["total_packs"], 1)
        self.assertEqual(result["total_assets"], 1)
        self.assertEqual(len(result["packs"]), 1)

        pack_result = result["packs"][0]
        self.assertEqual(pack_result["pack_id"], "test_pack")
        self.assertEqual(pack_result["title"], "Test Pack")
        self.assertEqual(len(pack_result["entries"]), 1)

        entry = pack_result["entries"][0]
        self.assertEqual(entry["asset_id"], "letter_A")
        self.assertEqual(entry["asset_name"], "Letter A")
        self.assertEqual(entry["thumbnail"], "renders/thumbnails/letter_A_thumb.png")
        self.assertEqual(entry["outputs"]["gif"], "renders/gif/letter_A_pulse.gif")
        self.assertNotIn("thumbnail", entry["outputs"])

    @patch("pipeline.packager.PackDefinition.from_file")
    @patch("pipeline.packager.build_pack")
    def test_generate_pipeline_manifest_skip_invalid_pack(self, mock_build_pack, mock_from_file):
        pack1_dir = os.path.join(self.packs_dir, "pack1")
        os.makedirs(pack1_dir)
        with open(os.path.join(pack1_dir, "pack.json"), "w") as f:
            json.dump({}, f)

        mock_from_file.side_effect = Exception("Invalid pack JSON")

        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
        )

        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        mock_build_pack.assert_not_called()

    @patch("pipeline.packager.PackDefinition.from_file")
    @patch("pipeline.packager.build_pack")
    def test_generate_pipeline_manifest_skip_build_pack_failure(self, mock_build_pack, mock_from_file):
        pack1_dir = os.path.join(self.packs_dir, "pack1")
        os.makedirs(pack1_dir)
        with open(os.path.join(pack1_dir, "pack.json"), "w") as f:
            json.dump({}, f)

        mock_pack = MagicMock()
        mock_pack.pack_id = "test_pack"
        mock_from_file.return_value = mock_pack

        mock_build_pack.side_effect = Exception("Build failed")

        result = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
        )

        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)

    def test_generate_pipeline_manifest_write_failure(self):
        # Provide an invalid path, e.g., a directory, to simulate a write failure
        invalid_path = os.path.join(self.temp_dir.name, "nonexistent_dir", "manifest.json")

        result = generate_pipeline_manifest(
            output_path=invalid_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
        )

        self.assertEqual(result["total_packs"], 0)
        # Verify file was not written because the directory doesn't exist
        self.assertFalse(os.path.exists(invalid_path))

if __name__ == '__main__':
    unittest.main()

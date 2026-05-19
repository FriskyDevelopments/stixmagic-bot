import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from pipeline.manifest import generate_pipeline_manifest

class TestPipelineManifest(unittest.TestCase):

    def test_generate_pipeline_manifest_no_packs(self):
        with tempfile.TemporaryDirectory() as packs_dir:
            with tempfile.NamedTemporaryFile() as out_file:
                manifest = generate_pipeline_manifest(
                    packs_dir=packs_dir,
                    output_path=out_file.name
                )
                self.assertEqual(manifest["total_packs"], 0)
                self.assertEqual(manifest["total_assets"], 0)
                self.assertEqual(manifest["packs"], [])

                with open(out_file.name, "r") as f:
                    data = json.load(f)
                    self.assertEqual(data["total_packs"], 0)

    @patch("pipeline.packager.PackDefinition.from_file")
    @patch("pipeline.manifest.build_pack", create=True)
    @patch("pipeline.manifest.AssetCatalog", create=True)
    def test_generate_pipeline_manifest_success(self, mock_AssetCatalog, mock_build_pack, mock_from_file):
        with tempfile.TemporaryDirectory() as packs_dir:
            # Create dummy pack directory
            pack_dir = os.path.join(packs_dir, "test_pack")
            os.makedirs(pack_dir)
            pack_json = os.path.join(pack_dir, "pack.json")
            with open(pack_json, "w") as f:
                f.write("{}")

            out_file_path = os.path.join(packs_dir, "out.json")

            # Set up mocks
            mock_pack = MagicMock()
            mock_pack.pack_id = "test_pack_id"
            mock_pack.title = "Test Pack"
            mock_pack.theme = "test_theme"
            mock_pack.target_platforms = ["tg"]
            mock_pack.export_formats = ["gif"]
            mock_from_file.return_value = mock_pack

            mock_pack_manifest = MagicMock()
            mock_entry = MagicMock()
            mock_entry.asset_id = "test_asset"
            mock_entry.preset_id = "test_preset"
            mock_entry.expected_outputs = {
                "thumbnail": "thumb.png",
                "gif": "out.gif"
            }
            mock_pack_manifest.entries = [mock_entry]
            mock_build_pack.return_value = mock_pack_manifest

            mock_catalog = mock_AssetCatalog.return_value
            mock_asset = MagicMock()
            mock_asset.name = "Test Asset Name"
            mock_asset.category.value = "test_category"
            mock_catalog.get.return_value = mock_asset

            with patch('pipeline.metadata.AssetCatalog', mock_AssetCatalog):
                with patch('pipeline.packager.build_pack', mock_build_pack):
                    manifest = generate_pipeline_manifest(
                        packs_dir=packs_dir,
                        output_path=out_file_path
                    )

            self.assertEqual(manifest["total_packs"], 1)
            self.assertEqual(manifest["total_assets"], 1)
            self.assertEqual(len(manifest["packs"]), 1)

            pack_data = manifest["packs"][0]
            self.assertEqual(pack_data["pack_id"], "test_pack_id")
            self.assertEqual(pack_data["title"], "Test Pack")

            entries = pack_data["entries"]
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["asset_id"], "test_asset")
            self.assertEqual(entry["thumbnail"], "thumb.png")
            self.assertEqual(entry["outputs"]["gif"], "out.gif")

            # verify JSON is written correctly
            with open(out_file_path, "r") as f:
                data = json.load(f)
                self.assertEqual(data["total_packs"], 1)

    @patch("pipeline.packager.PackDefinition.from_file")
    @patch("pipeline.metadata.AssetCatalog")
    def test_generate_pipeline_manifest_from_file_error(self, mock_AssetCatalog, mock_from_file):
        with tempfile.TemporaryDirectory() as packs_dir:
            pack_dir = os.path.join(packs_dir, "test_pack")
            os.makedirs(pack_dir)
            pack_json = os.path.join(pack_dir, "pack.json")
            with open(pack_json, "w") as f:
                f.write("{}")

            with tempfile.NamedTemporaryFile() as out_file:
                mock_from_file.side_effect = Exception("Failed to load pack")

                manifest = generate_pipeline_manifest(
                    packs_dir=packs_dir,
                    output_path=out_file.name
                )

                self.assertEqual(manifest["total_packs"], 0)
                self.assertEqual(manifest["total_assets"], 0)

    @patch("pipeline.packager.PackDefinition.from_file")
    @patch("pipeline.packager.build_pack")
    @patch("pipeline.metadata.AssetCatalog")
    def test_generate_pipeline_manifest_build_pack_error(self, mock_AssetCatalog, mock_build_pack, mock_from_file):
        with tempfile.TemporaryDirectory() as packs_dir:
            pack_dir = os.path.join(packs_dir, "test_pack")
            os.makedirs(pack_dir)
            pack_json = os.path.join(pack_dir, "pack.json")
            with open(pack_json, "w") as f:
                f.write("{}")

            with tempfile.NamedTemporaryFile() as out_file:
                mock_from_file.return_value = MagicMock()
                mock_build_pack.side_effect = Exception("Failed to build pack")

                manifest = generate_pipeline_manifest(
                    packs_dir=packs_dir,
                    output_path=out_file.name
                )

                self.assertEqual(manifest["total_packs"], 0)

    @patch("pipeline.manifest.open", side_effect=PermissionError("Permission denied"))
    @patch("pipeline.metadata.AssetCatalog")
    def test_generate_pipeline_manifest_write_error(self, mock_AssetCatalog, mock_open):
        with tempfile.TemporaryDirectory() as packs_dir:
            manifest = generate_pipeline_manifest(
                packs_dir=packs_dir,
                output_path="/nonexistent/path/out.json"
            )
            # The function should return normally, not crash
            self.assertIn("generated_at", manifest)

    @patch("pipeline.metadata.AssetCatalog")
    def test_generate_pipeline_manifest_catalog_path(self, mock_AssetCatalog):
        with tempfile.TemporaryDirectory() as packs_dir:
            with tempfile.NamedTemporaryFile() as out_file:
                generate_pipeline_manifest(
                    packs_dir=packs_dir,
                    output_path=out_file.name,
                    catalog_path="custom_catalog.json"
                )
                mock_AssetCatalog.assert_called_once_with(auto_load=True, path="custom_catalog.json")

if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest.mock import patch, MagicMock

from pipeline.manifest import generate_pipeline_manifest

class TestGeneratePipelineManifest(unittest.TestCase):
    @patch('pipeline.manifest.json.dump')
    @patch('pipeline.manifest.open', new_callable=unittest.mock.mock_open)
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.packager.PackDefinition')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_happy_path(self, mock_isfile, mock_isdir, mock_listdir, mock_asset_catalog, mock_pack_def, mock_build_pack, mock_open, mock_json_dump):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack1']
        mock_isfile.return_value = True

        mock_catalog_instance = MagicMock()
        mock_asset_catalog.return_value = mock_catalog_instance

        mock_asset = MagicMock()
        mock_asset.name = "Asset 1"
        mock_asset.category.value = "cat1"
        mock_catalog_instance.get.return_value = mock_asset

        mock_pack_instance = MagicMock()
        mock_pack_instance.pack_id = "pack1_id"
        mock_pack_instance.title = "Pack 1"
        mock_pack_instance.theme = "light"
        mock_pack_instance.target_platforms = ["web"]
        mock_pack_instance.export_formats = ["gif"]
        mock_pack_def.from_file.return_value = mock_pack_instance

        mock_pack_manifest = MagicMock()
        mock_entry = MagicMock()
        mock_entry.asset_id = "asset1_id"
        mock_entry.preset_id = "preset1"
        mock_entry.expected_outputs = {"thumbnail": "thumb.png", "gif": "out.gif"}
        mock_pack_manifest.entries = [mock_entry]
        mock_build_pack.return_value = mock_pack_manifest

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 1)
        self.assertEqual(result["total_assets"], 1)
        self.assertEqual(len(result["packs"]), 1)
        self.assertEqual(result["packs"][0]["pack_id"], "pack1_id")
        self.assertEqual(result["packs"][0]["entries"][0]["asset_id"], "asset1_id")

    @patch('pipeline.manifest.json.dump')
    @patch('pipeline.manifest.open', new_callable=unittest.mock.mock_open)
    @patch('pipeline.metadata.AssetCatalog')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_empty_packs_dir(self, mock_isdir, mock_listdir, mock_asset_catalog, mock_open, mock_json_dump):
        mock_isdir.return_value = True
        mock_listdir.return_value = []

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(len(result["packs"]), 0)

    @patch('pipeline.manifest.json.dump')
    @patch('pipeline.manifest.open', new_callable=unittest.mock.mock_open)
    @patch('pipeline.metadata.AssetCatalog')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_packs_dir_not_dir(self, mock_isdir, mock_listdir, mock_asset_catalog, mock_open, mock_json_dump):
        mock_isdir.return_value = False

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(len(result["packs"]), 0)

    @patch('pipeline.manifest.json.dump')
    @patch('pipeline.manifest.open', new_callable=unittest.mock.mock_open)
    @patch('pipeline.packager.PackDefinition')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_pack_def_exception(self, mock_isfile, mock_isdir, mock_listdir, mock_asset_catalog, mock_pack_def, mock_open, mock_json_dump):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack1']
        mock_isfile.return_value = True

        mock_pack_def.from_file.side_effect = Exception("Pack definition error")

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(len(result["packs"]), 0)

    @patch('pipeline.manifest.json.dump')
    @patch('pipeline.manifest.open', new_callable=unittest.mock.mock_open)
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.packager.PackDefinition')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_build_pack_exception(self, mock_isfile, mock_isdir, mock_listdir, mock_asset_catalog, mock_pack_def, mock_build_pack, mock_open, mock_json_dump):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack1']
        mock_isfile.return_value = True

        mock_pack_def.from_file.return_value = MagicMock()
        mock_build_pack.side_effect = Exception("Build pack error")

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(len(result["packs"]), 0)

    @patch('pipeline.manifest.open', new_callable=unittest.mock.mock_open)
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.packager.PackDefinition')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_file_write_exception(self, mock_isfile, mock_isdir, mock_listdir, mock_asset_catalog, mock_pack_def, mock_build_pack, mock_open):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack1']
        mock_isfile.return_value = True

        mock_catalog_instance = MagicMock()
        mock_asset_catalog.return_value = mock_catalog_instance

        mock_asset = MagicMock()
        mock_asset.name = "Asset 1"
        mock_asset.category.value = "cat1"
        mock_catalog_instance.get.return_value = mock_asset

        mock_pack_instance = MagicMock()
        mock_pack_instance.pack_id = "pack1_id"
        mock_pack_instance.title = "Pack 1"
        mock_pack_instance.theme = "light"
        mock_pack_instance.target_platforms = ["web"]
        mock_pack_instance.export_formats = ["gif"]
        mock_pack_def.from_file.return_value = mock_pack_instance

        mock_pack_manifest = MagicMock()
        mock_entry = MagicMock()
        mock_entry.asset_id = "asset1_id"
        mock_entry.preset_id = "preset1"
        mock_entry.expected_outputs = {"thumbnail": "thumb.png", "gif": "out.gif"}
        mock_pack_manifest.entries = [mock_entry]
        mock_build_pack.return_value = mock_pack_manifest

        mock_open.side_effect = IOError("File write error")

        # Function should catch and log exception, and still return the manifest dict
        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 1)
        self.assertEqual(result["total_assets"], 1)
        self.assertEqual(len(result["packs"]), 1)
        self.assertEqual(result["packs"][0]["pack_id"], "pack1_id")
        self.assertEqual(result["packs"][0]["entries"][0]["asset_id"], "asset1_id")

if __name__ == '__main__':
    unittest.main()

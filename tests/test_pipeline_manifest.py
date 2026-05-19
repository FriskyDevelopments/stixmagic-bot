import unittest
from unittest.mock import patch, MagicMock
from pipeline.manifest import generate_pipeline_manifest

class TestGeneratePipelineManifest(unittest.TestCase):

    @patch('pipeline.manifest.os.path.isdir')
    @patch('pipeline.manifest.os.listdir')
    @patch('pipeline.manifest.os.path.isfile')
    @patch('pipeline.packager.PackDefinition.from_file')
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_manifest_success(self, mock_json_dump, mock_open, MockCatalog, mock_build, mock_from_file, mock_isfile, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack_test']
        mock_isfile.return_value = True

        mock_pack = MagicMock()
        mock_pack.pack_id = "test_pack"
        mock_pack.title = "Test Pack"
        mock_pack.theme = "neon"
        mock_pack.target_platforms = ["telegram"]
        mock_pack.export_formats = ["webm"]
        mock_from_file.return_value = mock_pack

        mock_pack_manifest = MagicMock()
        mock_entry = MagicMock()
        mock_entry.asset_id = "test_asset"
        mock_entry.preset_id = "pulse"
        mock_entry.expected_outputs = {
            "thumbnail": "renders/thumbnails/test_asset_thumb.png",
            "webm": "renders/webm/test_asset_pulse.webm"
        }
        mock_pack_manifest.entries = [mock_entry]
        mock_build.return_value = mock_pack_manifest

        mock_catalog_instance = MagicMock()
        mock_asset = MagicMock()
        mock_asset.name = "Test Asset"
        mock_asset.category.value = "test_category"
        mock_catalog_instance.get.return_value = mock_asset
        MockCatalog.return_value = mock_catalog_instance

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 1)
        self.assertEqual(result["total_assets"], 1)
        self.assertEqual(result["packs"][0]["pack_id"], "test_pack")
        self.assertEqual(result["packs"][0]["entries"][0]["asset_id"], "test_asset")

    @patch('pipeline.manifest.os.path.isdir')
    @patch('pipeline.manifest.os.listdir')
    @patch('pipeline.manifest.os.path.isfile')
    @patch('pipeline.packager.PackDefinition.from_file')
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_manifest_no_packs_dir(self, mock_json_dump, mock_open, MockCatalog, mock_build, mock_from_file, mock_isfile, mock_listdir, mock_isdir):
        mock_isdir.return_value = False

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 0)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(result["packs"], [])

    @patch('pipeline.manifest.os.path.isdir')
    @patch('pipeline.manifest.os.listdir')
    @patch('pipeline.manifest.os.path.isfile')
    @patch('pipeline.packager.PackDefinition.from_file')
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_manifest_pack_load_error(self, mock_json_dump, mock_open, MockCatalog, mock_build, mock_from_file, mock_isfile, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack_test']
        mock_isfile.return_value = True

        mock_from_file.side_effect = Exception("Failed to load")

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 0)

    @patch('pipeline.manifest.os.path.isdir')
    @patch('pipeline.manifest.os.listdir')
    @patch('pipeline.manifest.os.path.isfile')
    @patch('pipeline.packager.PackDefinition.from_file')
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_manifest_build_pack_error(self, mock_json_dump, mock_open, MockCatalog, mock_build, mock_from_file, mock_isfile, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack_test']
        mock_isfile.return_value = True

        mock_pack = MagicMock()
        mock_from_file.return_value = mock_pack

        mock_build.side_effect = Exception("Failed to build")

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 0)

    @patch('pipeline.manifest.os.path.isdir')
    @patch('pipeline.manifest.os.listdir')
    @patch('pipeline.manifest.os.path.isfile')
    @patch('pipeline.packager.PackDefinition.from_file')
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_manifest_file_write_error(self, mock_json_dump, mock_open, MockCatalog, mock_build, mock_from_file, mock_isfile, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack_test']
        mock_isfile.return_value = True

        mock_pack = MagicMock()
        mock_pack.pack_id = "test_pack"
        mock_from_file.return_value = mock_pack

        mock_pack_manifest = MagicMock()
        mock_pack_manifest.entries = []
        mock_build.return_value = mock_pack_manifest

        mock_open.side_effect = Exception("Failed to open file")

        # Should not raise exception, but still return result
        result = generate_pipeline_manifest(output_path="test_manifest.json")
        self.assertEqual(result["total_packs"], 1)

    @patch('pipeline.manifest.os.path.isdir')
    @patch('pipeline.manifest.os.listdir')
    @patch('pipeline.manifest.os.path.isfile')
    @patch('pipeline.packager.PackDefinition.from_file')
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_manifest_missing_asset_in_catalog(self, mock_json_dump, mock_open, MockCatalog, mock_build, mock_from_file, mock_isfile, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ['pack_test']
        mock_isfile.return_value = True

        mock_pack = MagicMock()
        mock_pack.pack_id = "test_pack"
        mock_pack.title = "Test Pack"
        mock_pack.theme = "neon"
        mock_pack.target_platforms = ["telegram"]
        mock_pack.export_formats = ["webm"]
        mock_from_file.return_value = mock_pack

        mock_pack_manifest = MagicMock()
        mock_entry = MagicMock()
        mock_entry.asset_id = "test_asset"
        mock_entry.preset_id = "pulse"
        mock_entry.expected_outputs = {
            "thumbnail": "renders/thumbnails/test_asset_thumb.png",
            "webm": "renders/webm/test_asset_pulse.webm"
        }
        mock_pack_manifest.entries = [mock_entry]
        mock_build.return_value = mock_pack_manifest

        mock_catalog_instance = MagicMock()
        # Catalog get returns None to simulate missing asset
        mock_catalog_instance.get.return_value = None
        MockCatalog.return_value = mock_catalog_instance

        result = generate_pipeline_manifest(output_path="test_manifest.json")

        self.assertEqual(result["total_packs"], 1)
        self.assertEqual(result["total_assets"], 1)
        self.assertEqual(result["packs"][0]["entries"][0]["asset_id"], "test_asset")
        self.assertEqual(result["packs"][0]["entries"][0]["asset_name"], "test_asset")
        self.assertEqual(result["packs"][0]["entries"][0]["asset_category"], "")

    @patch('pipeline.manifest.os.path.isdir')
    @patch('pipeline.manifest.os.listdir')
    @patch('pipeline.manifest.os.path.isfile')
    @patch('pipeline.packager.PackDefinition.from_file')
    @patch('pipeline.packager.build_pack')
    @patch('pipeline.metadata.AssetCatalog')
    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_manifest_with_catalog_path(self, mock_json_dump, mock_open, MockCatalog, mock_build, mock_from_file, mock_isfile, mock_listdir, mock_isdir):
        mock_isdir.return_value = False

        result = generate_pipeline_manifest(output_path="test_manifest.json", catalog_path="custom_catalog.json")

        MockCatalog.assert_called_once_with(auto_load=True, path="custom_catalog.json")

if __name__ == '__main__':
    unittest.main()

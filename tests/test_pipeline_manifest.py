import unittest
from unittest.mock import patch, MagicMock
from pipeline.manifest import build_pipeline_manifest
from pipeline.packager import PackDefinition

class TestPipelineManifest(unittest.TestCase):
    @patch("pipeline.packager.build_pack")
    def test_build_pipeline_manifest(self, mock_build_pack):
        # Setup mock PackManifest from build_pack
        mock_pack_manifest = MagicMock()

        mock_entry = MagicMock()
        mock_entry.asset_id = "test_asset"
        mock_entry.preset_id = "test_preset"
        mock_entry.expected_outputs = {
            "thumbnail": "thumb.png",
            "gif": "output.gif"
        }
        mock_pack_manifest.entries = [mock_entry]
        mock_build_pack.return_value = mock_pack_manifest

        # Setup mock AssetCatalog
        mock_catalog = MagicMock()
        mock_asset = MagicMock()
        mock_asset.name = "Test Asset"
        mock_asset.category.value = "test_category"
        mock_catalog.get.return_value = mock_asset

        # Setup PackDefinition
        pack = PackDefinition(
            pack_id="test_pack",
            title="Test Pack",
            theme="test_theme",
            target_platforms=["platform1"],
            export_formats=["gif"]
        )

        manifest = build_pipeline_manifest([pack], mock_catalog, renders_root="renders")

        self.assertIn("generated_at", manifest)
        self.assertEqual(manifest["total_packs"], 1)
        self.assertEqual(manifest["total_assets"], 1)
        self.assertEqual(len(manifest["packs"]), 1)

        pack_data = manifest["packs"][0]
        self.assertEqual(pack_data["pack_id"], "test_pack")
        self.assertEqual(pack_data["title"], "Test Pack")
        self.assertEqual(pack_data["theme"], "test_theme")
        self.assertEqual(pack_data["target_platforms"], ["platform1"])
        self.assertEqual(pack_data["export_formats"], ["gif"])

        self.assertEqual(len(pack_data["entries"]), 1)
        entry_data = pack_data["entries"][0]
        self.assertEqual(entry_data["asset_id"], "test_asset")
        self.assertEqual(entry_data["asset_name"], "Test Asset")
        self.assertEqual(entry_data["asset_category"], "test_category")
        self.assertEqual(entry_data["preset_id"], "test_preset")
        self.assertEqual(entry_data["thumbnail"], "thumb.png")
        self.assertEqual(entry_data["outputs"], {"gif": "output.gif"})

if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from pipeline.manifest import generate_pipeline_manifest
from pipeline.packager import PackDefinition, PackManifest, PackManifestEntry
from pipeline.asset_model import Asset, AssetCategory, SourceFormat

class TestManifestGeneration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.packs_dir = os.path.join(self.temp_dir.name, "packs")
        self.renders_root = os.path.join(self.temp_dir.name, "renders")
        self.output_path = os.path.join(self.temp_dir.name, "pipeline_manifest.json")
        self.catalog_path = os.path.join(self.temp_dir.name, "catalog.json")

        os.makedirs(self.packs_dir)

        # Write an empty catalog
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    def tearDown(self):
        self.temp_dir.cleanup()


    def test_empty_pack_directory(self):
        # When packs_dir is empty
        manifest = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
            catalog_path=self.catalog_path
        )

        self.assertEqual(manifest["total_packs"], 0)
        self.assertEqual(manifest["total_assets"], 0)
        self.assertEqual(manifest["packs"], [])

        # Check that file was created and contains correct json
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, "r", encoding="utf-8") as f:
            written_manifest = json.load(f)
            self.assertEqual(written_manifest["total_packs"], 0)
            self.assertEqual(written_manifest["packs"], [])

    def test_missing_pack_directory(self):
        # When packs_dir doesnt exist at all
        manifest = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=os.path.join(self.temp_dir.name, "nonexistent"),
            renders_root=self.renders_root,
            catalog_path=self.catalog_path
        )

        self.assertEqual(manifest["total_packs"], 0)
        self.assertEqual(manifest["packs"], [])

    def test_invalid_pack_json(self):
        # Create a pack with an invalid json file
        pack_dir = os.path.join(self.packs_dir, "bad_pack")
        os.makedirs(pack_dir)
        with open(os.path.join(pack_dir, "pack.json"), "w", encoding="utf-8") as f:
            f.write("{ invalid json")

        # Create a pack with a valid json file to ensure we don't abort completely
        good_pack_dir = os.path.join(self.packs_dir, "good_pack")
        os.makedirs(good_pack_dir)

        valid_pack = PackDefinition(pack_id="good_pack", title="Good Pack")
        valid_pack.save(os.path.join(good_pack_dir, "pack.json"))

        manifest = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
            catalog_path=self.catalog_path
        )

        # Only the good pack should be generated
        self.assertEqual(manifest["total_packs"], 1)
        self.assertEqual(manifest["packs"][0]["pack_id"], "good_pack")


    @patch('pipeline.packager.build_pack')
    def test_successful_manifest_generation(self, mock_build_pack):
        # Create a valid pack.json
        pack_dir = os.path.join(self.packs_dir, "test_pack")
        os.makedirs(pack_dir)
        valid_pack = PackDefinition(
            pack_id="test_pack",
            title="Test Pack",
            theme="test_theme",
            export_formats=["gif", "png_sequence"],
            target_platforms=["telegram"]
        )
        valid_pack.save(os.path.join(pack_dir, "pack.json"))

        # Setup mock for AssetCatalog
        asset1 = Asset(id="asset_1", name="Asset 1", category=AssetCategory.LETTER, source_format=SourceFormat.SVG, source_path="asset_1.svg")
        asset2 = Asset(id="asset_2", name="Asset 2", category=AssetCategory.SYMBOL, source_format=SourceFormat.SVG, source_path="asset_2.svg")

        # Create a fake catalog
        catalog_data = [asset1.to_dict(), asset2.to_dict()]
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f)

        # Setup mock for build_pack
        manifest_entry1 = PackManifestEntry(
            asset_id="asset_1",
            preset_id="preset_a",
            expected_outputs={
                "thumbnail": "renders/thumbnails/asset_1_thumb.png",
                "gif": "renders/gif/asset_1_preset_a.gif",
            }
        )
        manifest_entry2 = PackManifestEntry(
            asset_id="asset_2",
            preset_id="preset_b",
            expected_outputs={
                "thumbnail": "renders/thumbnails/asset_2_thumb.png",
                "gif": "renders/gif/asset_2_preset_b.gif",
            }
        )

        mock_manifest = PackManifest(pack_id="test_pack", entries=[manifest_entry1, manifest_entry2])
        mock_build_pack.return_value = mock_manifest

        # Generate manifest
        manifest = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
            catalog_path=self.catalog_path
        )

        # Verify result
        self.assertEqual(manifest["total_packs"], 1)
        self.assertEqual(manifest["total_assets"], 2)

        pack = manifest["packs"][0]
        self.assertEqual(pack["pack_id"], "test_pack")
        self.assertEqual(pack["title"], "Test Pack")
        self.assertEqual(pack["theme"], "test_theme")
        self.assertEqual(pack["export_formats"], ["gif", "png_sequence"])
        self.assertEqual(pack["target_platforms"], ["telegram"])

        self.assertEqual(len(pack["entries"]), 2)

        entry1 = pack["entries"][0]
        self.assertEqual(entry1["asset_id"], "asset_1")
        self.assertEqual(entry1["asset_name"], "Asset 1")
        self.assertEqual(entry1["asset_category"], "letter")
        self.assertEqual(entry1["preset_id"], "preset_a")
        self.assertEqual(entry1["thumbnail"], "renders/thumbnails/asset_1_thumb.png")
        self.assertEqual(entry1["outputs"]["gif"], "renders/gif/asset_1_preset_a.gif")

        # Check that 'thumbnail' is not duplicated in 'outputs'
        self.assertNotIn("thumbnail", entry1["outputs"])

        mock_build_pack.assert_called_once()

    @patch('pipeline.packager.build_pack')
    def test_build_pack_failure_skipped(self, mock_build_pack):
        # Test that if build_pack fails, the pack is skipped but execution continues
        pack_dir1 = os.path.join(self.packs_dir, "pack1")
        pack_dir2 = os.path.join(self.packs_dir, "pack2")
        os.makedirs(pack_dir1)
        os.makedirs(pack_dir2)

        PackDefinition(pack_id="pack1", title="Pack 1").save(os.path.join(pack_dir1, "pack.json"))
        PackDefinition(pack_id="pack2", title="Pack 2").save(os.path.join(pack_dir2, "pack.json"))

        # Make the first call fail and the second call succeed
        def build_pack_side_effect(pack, *args, **kwargs):
            if pack.pack_id == "pack1":
                raise ValueError("Simulated build pack error")
            return PackManifest(pack_id="pack2", entries=[])

        mock_build_pack.side_effect = build_pack_side_effect

        manifest = generate_pipeline_manifest(
            output_path=self.output_path,
            packs_dir=self.packs_dir,
            renders_root=self.renders_root,
            catalog_path=self.catalog_path
        )

        self.assertEqual(manifest["total_packs"], 1)
        self.assertEqual(manifest["packs"][0]["pack_id"], "pack2")

if __name__ == "__main__":
    unittest.main()

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.asset_model.asset import Asset
from pipeline.metadata.registry import AssetRegistry


class TestAssetRegistry(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to act as the source directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.source_path = Path(self.temp_dir.name).resolve()

        # Valid asset data
        self.asset1_data = {
            "id": "asset1",
            "name": "Asset 1",
            "category": "letter",
            "theme": "neon",
            "source_format": "png",
            "source_path": "letters/asset1.png",
            "width": 100,
            "height": 100,
            "tags": ["tag1", "common"],
            "animation_compatible_presets": ["preset1"],
        }
        self.asset2_data = {
            "id": "asset2",
            "name": "Asset 2",
            "category": "symbol",
            "theme": "cloud",
            "source_format": "svg",
            "source_path": "symbols/asset2.svg",
            "width": 200,
            "height": 200,
            "tags": ["tag2", "common"],
            "animation_compatible_presets": [],
        }

        # Create subdirectories and valid JSON files
        (self.source_path / "letters").mkdir(parents=True, exist_ok=True)
        (self.source_path / "symbols").mkdir(parents=True, exist_ok=True)

        with open(
            self.source_path / "letters" / "asset1.json", "w", encoding="utf-8"
        ) as f:
            json.dump(self.asset1_data, f)

        with open(
            self.source_path / "symbols" / "asset2.json", "w", encoding="utf-8"
        ) as f:
            json.dump(self.asset2_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_and_load_success(self):
        registry = AssetRegistry(source_dir=str(self.source_path))
        self.assertEqual(len(registry), 2)

        asset1 = registry.get("asset1")
        self.assertIsNotNone(asset1)
        self.assertEqual(asset1.name, "Asset 1")

    @patch("pipeline.metadata.registry.logger")
    def test_load_missing_dir(self, mock_logger):
        non_existent_dir = self.source_path / "does_not_exist"
        registry = AssetRegistry(source_dir=str(non_existent_dir))

        self.assertEqual(len(registry), 0)
        mock_logger.warning.assert_called_once()
        self.assertIn(
            "Asset source directory not found", mock_logger.warning.call_args[0][0]
        )

    @patch("pipeline.metadata.registry.logger")
    def test_load_invalid_json(self, mock_logger):
        # Create an invalid JSON file
        invalid_path = self.source_path / "invalid.json"
        with open(invalid_path, "w", encoding="utf-8") as f:
            f.write("not valid json")

        registry = AssetRegistry(source_dir=str(self.source_path))

        # Should still load the 2 valid assets
        self.assertEqual(len(registry), 2)
        mock_logger.error.assert_called_once()
        self.assertIn("Failed to load asset", mock_logger.error.call_args[0][0])

    def test_reload(self):
        registry = AssetRegistry(source_dir=str(self.source_path))
        self.assertEqual(len(registry), 2)

        # Add a new asset directly to the file system
        asset3_data = dict(self.asset1_data)
        asset3_data["id"] = "asset3"
        with open(
            self.source_path / "letters" / "asset3.json", "w", encoding="utf-8"
        ) as f:
            json.dump(asset3_data, f)

        # Registry shouldn't have it yet
        self.assertEqual(len(registry), 2)
        self.assertIsNone(registry.get("asset3"))

        # Reload
        registry.reload()

        # Now it should be there
        self.assertEqual(len(registry), 3)
        self.assertIsNotNone(registry.get("asset3"))

    def test_queries(self):
        registry = AssetRegistry(source_dir=str(self.source_path))

        # get()
        self.assertEqual(registry.get("asset1").id, "asset1")
        self.assertIsNone(registry.get("nonexistent"))

        # all()
        all_assets = registry.all()
        self.assertEqual(len(all_assets), 2)
        self.assertIn("asset1", [a.id for a in all_assets])
        self.assertIn("asset2", [a.id for a in all_assets])

        # get_by_category()
        letters = registry.get_by_category("letter")
        self.assertEqual(len(letters), 1)
        self.assertEqual(letters[0].id, "asset1")

        # get_by_theme()
        clouds = registry.get_by_theme("cloud")
        self.assertEqual(len(clouds), 1)
        self.assertEqual(clouds[0].id, "asset2")

        # get_by_tag()
        tags_common = registry.get_by_tag("common")
        self.assertEqual(len(tags_common), 2)
        tags_tag1 = registry.get_by_tag("tag1")
        self.assertEqual(len(tags_tag1), 1)
        self.assertEqual(tags_tag1[0].id, "asset1")

        # get_compatible()
        # asset1 is compatible only with "preset1" (or none if list was empty, but it has preset1)
        # asset2 is compatible with anything because list is empty
        compat_preset1 = registry.get_compatible("preset1")
        self.assertEqual(len(compat_preset1), 2)  # asset1 and asset2

        compat_preset2 = registry.get_compatible("preset2")
        self.assertEqual(len(compat_preset2), 1)  # only asset2

    def test_register_and_save(self):
        registry = AssetRegistry(source_dir=str(self.source_path))

        new_asset = Asset(
            id="new_asset",
            name="New Asset",
            category="letter",
            theme="neon",
            source_format="png",
            source_path="letters/new_asset.png",
            width=50,
            height=50,
        )

        # Register updates memory but not disk
        registry.register(new_asset)
        self.assertEqual(len(registry), 3)
        self.assertIsNotNone(registry.get("new_asset"))

        # The file shouldn't exist yet
        new_asset_path = self.source_path / "letters" / "new_asset.json"
        self.assertFalse(new_asset_path.exists())

        # Save updates disk
        saved_path = registry.save(new_asset)
        self.assertEqual(saved_path, str(new_asset_path))
        self.assertTrue(new_asset_path.exists())

        # Verify saved contents
        with open(new_asset_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            self.assertEqual(saved_data["id"], "new_asset")

    def test_dunder_methods(self):
        registry = AssetRegistry(source_dir=str(self.source_path))

        # __len__
        self.assertEqual(len(registry), 2)

        # __repr__
        repr_str = repr(registry)
        self.assertIn("AssetRegistry assets=2", repr_str)
        self.assertIn(str(self.source_path), repr_str)


if __name__ == "__main__":
    unittest.main()

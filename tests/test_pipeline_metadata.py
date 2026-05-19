import os
import json
import tempfile
import unittest
from unittest.mock import patch

from pipeline.metadata import AssetCatalog, CatalogValidationError, _validate_raw_asset
from pipeline.asset_model import Asset, AssetCategory, AssetTheme, SourceFormat

class TestPipelineMetadata(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.catalog_path = os.path.join(self.temp_dir.name, "catalog.json")

        self.valid_raw_asset = {
            "id": "asset_1",
            "name": "Asset One",
            "category": "letter",
            "source_format": "png",
            "source_path": "path/to/asset.png",
            "width": 512,
            "height": 512,
            "transparent_background": True,
            "tags": ["tag1", "tag2"],
            "animation_compatible_presets": [],
            "export_targets": [],
            "notes": ""
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_raw_asset_valid(self):
        # Should not raise
        _validate_raw_asset(self.valid_raw_asset, 0)

    def test_validate_raw_asset_not_dict(self):
        with self.assertRaisesRegex(CatalogValidationError, "not a JSON object"):
            _validate_raw_asset([], 0)

    def test_validate_raw_asset_missing_field(self):
        del self.valid_raw_asset["name"]
        with self.assertRaisesRegex(CatalogValidationError, "missing required field"):
            _validate_raw_asset(self.valid_raw_asset, 0)

    def test_validate_raw_asset_invalid_type(self):
        self.valid_raw_asset["name"] = 123
        with self.assertRaisesRegex(CatalogValidationError, "must be a string"):
            _validate_raw_asset(self.valid_raw_asset, 0)

    def test_validate_raw_asset_empty_id(self):
        self.valid_raw_asset["id"] = "   "
        with self.assertRaisesRegex(CatalogValidationError, "empty 'id' field"):
            _validate_raw_asset(self.valid_raw_asset, 0)

    def test_catalog_load_missing_file(self):
        catalog = AssetCatalog(self.catalog_path)
        catalog.load()
        self.assertEqual(len(catalog), 0)

    def test_catalog_load_invalid_json(self):
        with open(self.catalog_path, "w") as f:
            f.write("{invalid_json:")

        catalog = AssetCatalog(self.catalog_path)
        # strict=False should just log and return
        catalog.load(strict=False)
        self.assertEqual(len(catalog), 0)

        # strict=True should raise
        with self.assertRaises(CatalogValidationError):
            catalog.load(strict=True)

    def test_catalog_load_not_list(self):
        with open(self.catalog_path, "w") as f:
            f.write('{"id": "asset_1"}')

        catalog = AssetCatalog(self.catalog_path)
        catalog.load(strict=False)
        self.assertEqual(len(catalog), 0)

        with self.assertRaises(CatalogValidationError):
            catalog.load(strict=True)

    def test_catalog_load_valid_and_invalid_entries(self):
        invalid_asset = self.valid_raw_asset.copy()
        del invalid_asset["name"]

        with open(self.catalog_path, "w") as f:
            json.dump([self.valid_raw_asset, invalid_asset], f)

        catalog = AssetCatalog(self.catalog_path)

        # strict=False should load the valid one and skip the invalid one
        catalog.load(strict=False)
        self.assertEqual(len(catalog), 1)
        self.assertIsNotNone(catalog.get("asset_1"))

        # strict=True should raise on the invalid one
        with self.assertRaises(CatalogValidationError):
            catalog.load(strict=True)

    def test_catalog_save(self):
        catalog = AssetCatalog(self.catalog_path)
        asset = Asset.from_dict(self.valid_raw_asset)
        catalog.add(asset)

        catalog.save()

        self.assertTrue(os.path.exists(self.catalog_path))
        with open(self.catalog_path, "r") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "asset_1")

    def test_crud_operations(self):
        catalog = AssetCatalog(self.catalog_path)
        asset = Asset.from_dict(self.valid_raw_asset)

        # Add
        catalog.add(asset)
        self.assertEqual(len(catalog), 1)

        # Get
        retrieved = catalog.get("asset_1")
        self.assertEqual(retrieved, asset)
        self.assertIsNone(catalog.get("nonexistent"))

        # All
        self.assertEqual(catalog.all(), [asset])

        # Remove
        self.assertTrue(catalog.remove("asset_1"))
        self.assertEqual(len(catalog), 0)
        self.assertFalse(catalog.remove("asset_1"))

    def test_querying(self):
        catalog = AssetCatalog(self.catalog_path)

        asset1 = Asset.from_dict(self.valid_raw_asset)
        asset1.theme = AssetTheme.NEON
        asset1.tags = ["hello", "world"]

        asset2 = Asset.from_dict(self.valid_raw_asset)
        asset2.id = "asset_2"
        asset2.category = AssetCategory.NUMBER
        asset2.theme = AssetTheme.CLOUD
        asset2.tags = ["world", "peace"]
        asset2.animation_compatible_presets = ["preset1"]

        catalog.add(asset1)
        catalog.add(asset2)

        self.assertEqual(catalog.by_category(AssetCategory.LETTER), [asset1])
        self.assertEqual(catalog.by_category(AssetCategory.NUMBER), [asset2])

        self.assertEqual(catalog.by_theme(AssetTheme.NEON), [asset1])
        self.assertEqual(catalog.by_theme(AssetTheme.CLOUD), [asset2])

        self.assertEqual(catalog.search("hello"), [asset1])
        self.assertEqual(catalog.search("WORLD"), [asset1, asset2])
        self.assertEqual(catalog.search("nonexistent"), [])

        # asset1 is compatible with all because empty list
        # asset2 is only compatible with "preset1"
        self.assertEqual(catalog.by_preset("preset1"), [asset1, asset2])
        self.assertEqual(catalog.by_preset("preset2"), [asset1])

if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from pipeline.asset_model import Asset, AssetCategory, AssetTheme, SourceFormat
from pipeline.metadata import AssetCatalog, CatalogValidationError, _validate_raw_asset

class TestAssetCatalogValidation(unittest.TestCase):
    def test_validate_raw_asset_valid(self):
        valid_raw = {
            "id": "test_asset",
            "name": "Test Asset",
            "category": "letter",
            "source_format": "png",
            "source_path": "letters/test_asset.png"
        }
        # Should not raise any exception
        _validate_raw_asset(valid_raw, 0)

    def test_validate_raw_asset_not_dict(self):
        with self.assertRaisesRegex(CatalogValidationError, r"Catalog entry \[0\] is not a JSON object"):
            _validate_raw_asset(["not", "a", "dict"], 0)

    def test_validate_raw_asset_missing_fields(self):
        invalid_raw = {
            "id": "test_asset",
            "name": "Test Asset"
            # Missing category, source_format, source_path
        }
        with self.assertRaisesRegex(CatalogValidationError, r"missing required field\(s\)"):
            _validate_raw_asset(invalid_raw, 0)

    def test_validate_raw_asset_wrong_type(self):
        invalid_raw = {
            "id": "test_asset",
            "name": 123,  # Should be string
            "category": "letter",
            "source_format": "png",
            "source_path": "letters/test_asset.png"
        }
        with self.assertRaisesRegex(CatalogValidationError, r"must be a string"):
            _validate_raw_asset(invalid_raw, 0)

    def test_validate_raw_asset_empty_id(self):
        invalid_raw = {
            "id": "   ",
            "name": "Test Asset",
            "category": "letter",
            "source_format": "png",
            "source_path": "letters/test_asset.png"
        }
        with self.assertRaisesRegex(CatalogValidationError, r"empty 'id' field"):
            _validate_raw_asset(invalid_raw, 0)


class TestAssetCatalog(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.catalog_path = os.path.join(self.temp_dir.name, "catalog.json")
        self.catalog = AssetCatalog(path=self.catalog_path, auto_load=False)

        self.sample_asset_dict = {
            "id": "letter_A",
            "name": "Letter A",
            "category": "letter",
            "source_format": "png",
            "source_path": "letters/A.png",
            "theme": "neon",
            "width": 512,
            "height": 512,
            "tags": ["alphabet", "vowel"],
            "animation_compatible_presets": ["preset1"],
            "export_targets": ["gif"]
        }
        self.sample_asset = Asset.from_dict(self.sample_asset_dict)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_missing_file(self):
        # Should not raise exception
        self.catalog.load()
        self.assertEqual(len(self.catalog), 0)

    def test_load_invalid_json(self):
        with open(self.catalog_path, "w") as f:
            f.write("not valid json")

        self.catalog.load(strict=False)
        self.assertEqual(len(self.catalog), 0)

        with self.assertRaises(CatalogValidationError):
            self.catalog.load(strict=True)

    def test_load_not_a_list(self):
        with open(self.catalog_path, "w") as f:
            json.dump({"not": "a list"}, f)

        self.catalog.load(strict=False)
        self.assertEqual(len(self.catalog), 0)

        with self.assertRaises(CatalogValidationError):
            self.catalog.load(strict=True)

    def test_load_with_validation_errors(self):
        data = [
            self.sample_asset_dict,
            {"id": "invalid_item"} # missing fields
        ]
        with open(self.catalog_path, "w") as f:
            json.dump(data, f)

        # strict=False should skip the invalid entry
        self.catalog.load(strict=False)
        self.assertEqual(len(self.catalog), 1)
        self.assertIsNotNone(self.catalog.get("letter_A"))

        # strict=True should raise
        with self.assertRaises(CatalogValidationError):
            self.catalog.load(strict=True)

    def test_load_success(self):
        with open(self.catalog_path, "w") as f:
            json.dump([self.sample_asset_dict], f)

        self.catalog.load()
        self.assertEqual(len(self.catalog), 1)
        self.assertEqual(self.catalog.get("letter_A").name, "Letter A")

    def test_save(self):
        self.catalog.add(self.sample_asset)
        self.catalog.save()

        self.assertTrue(os.path.exists(self.catalog_path))
        with open(self.catalog_path, "r") as f:
            data = json.load(f)

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "letter_A")

    def test_crud_operations(self):
        # get empty
        self.assertIsNone(self.catalog.get("nonexistent"))

        # add
        self.catalog.add(self.sample_asset)
        self.assertEqual(len(self.catalog), 1)

        # get
        asset = self.catalog.get("letter_A")
        self.assertIsNotNone(asset)
        self.assertEqual(asset.id, "letter_A")

        # all
        all_assets = self.catalog.all()
        self.assertEqual(len(all_assets), 1)
        self.assertEqual(all_assets[0], self.sample_asset)

        # remove
        self.assertTrue(self.catalog.remove("letter_A"))
        self.assertFalse(self.catalog.remove("nonexistent"))
        self.assertEqual(len(self.catalog), 0)

    def test_queries(self):
        asset1 = Asset.from_dict(self.sample_asset_dict)

        asset2_dict = self.sample_asset_dict.copy()
        asset2_dict.update({
            "id": "symbol_B",
            "category": "symbol",
            "theme": "cloud",
            "tags": ["consonant", "letter"],
            "animation_compatible_presets": [] # all compatible
        })
        asset2 = Asset.from_dict(asset2_dict)

        self.catalog.add(asset1)
        self.catalog.add(asset2)

        # by_category
        res = self.catalog.by_category(AssetCategory.LETTER)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, "letter_A")

        # by_theme
        res = self.catalog.by_theme(AssetTheme.CLOUD)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, "symbol_B")

        # by_preset
        res = self.catalog.by_preset("preset1")
        self.assertEqual(len(res), 2) # asset2 has empty compatible list (all allowed)

        res2 = self.catalog.by_preset("unknown_preset")
        self.assertEqual(len(res2), 1) # asset2 allows all, asset1 only preset1
        self.assertEqual(res2[0].id, "symbol_B")

        # search
        res = self.catalog.search("AlpHaBet") # case insensitive
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, "letter_A")

        res = self.catalog.search("nonexistent")
        self.assertEqual(len(res), 0)

    def test_dunder_methods(self):
        self.assertEqual(len(self.catalog), 0)
        self.catalog.add(self.sample_asset)
        self.assertEqual(len(self.catalog), 1)

        rep = repr(self.catalog)
        self.assertIn("AssetCatalog", rep)
        self.assertIn(self.catalog_path, rep)
        self.assertIn("count=1", rep)

if __name__ == "__main__":
    unittest.main()

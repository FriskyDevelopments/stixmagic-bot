import json
import os
import tempfile
import unittest
from unittest.mock import patch

from pipeline.asset_model import Asset, AssetCategory, AssetTheme, SourceFormat
from pipeline.metadata import (
    AssetCatalog,
    CatalogValidationError,
    _validate_raw_asset,
)


class TestPipelineMetadata(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.catalog_path = os.path.join(self.temp_dir.name, "catalog.json")
        self.catalog = AssetCatalog(path=self.catalog_path, auto_load=False)

        self.valid_asset_dict = {
            "id": "letter_A",
            "name": "Letter A",
            "category": "letter",
            "source_format": "png",
            "source_path": "assets/source/letter_A.png",
            "width": 512,
            "height": 512,
            "transparent_background": True,
            "theme": "neon",
            "tags": ["alphabet", "A"],
            "animation_compatible_presets": ["pulse", "glow"],
            "export_targets": ["gif", "webp"],
            "notes": "Test asset"
        }

        self.valid_asset = Asset.from_dict(self.valid_asset_dict)

    def tearDown(self):
        self.temp_dir.cleanup()

    # ── _validate_raw_asset tests ─────────────────────────────

    def test_validate_raw_asset_valid(self):
        # Should not raise
        _validate_raw_asset(self.valid_asset_dict, 0)

    def test_validate_raw_asset_not_dict(self):
        with self.assertRaisesRegex(CatalogValidationError, "not a JSON object"):
            _validate_raw_asset("not a dict", 0)

    def test_validate_raw_asset_missing_fields(self):
        invalid = self.valid_asset_dict.copy()
        del invalid["name"]
        with self.assertRaisesRegex(CatalogValidationError, "missing required field"):
            _validate_raw_asset(invalid, 0)

    def test_validate_raw_asset_non_string_field(self):
        invalid = self.valid_asset_dict.copy()
        invalid["name"] = 123
        with self.assertRaisesRegex(CatalogValidationError, "must be a string"):
            _validate_raw_asset(invalid, 0)

    def test_validate_raw_asset_empty_id(self):
        invalid = self.valid_asset_dict.copy()
        invalid["id"] = "   "
        with self.assertRaisesRegex(CatalogValidationError, "empty 'id' field"):
            _validate_raw_asset(invalid, 0)

    # ── AssetCatalog.load tests ───────────────────────────────

    def test_load_missing_file(self):
        self.catalog.load()
        self.assertEqual(len(self.catalog), 0)

    def test_load_invalid_json_non_strict(self):
        with open(self.catalog_path, "w") as fh:
            fh.write("invalid json")
        # Should not raise in non-strict mode
        self.catalog.load(strict=False)
        self.assertEqual(len(self.catalog), 0)

    def test_load_invalid_json_strict(self):
        with open(self.catalog_path, "w") as fh:
            fh.write("invalid json")
        with self.assertRaises(CatalogValidationError):
            self.catalog.load(strict=True)

    def test_load_not_list_non_strict(self):
        with open(self.catalog_path, "w") as fh:
            json.dump({"not": "a list"}, fh)
        self.catalog.load(strict=False)
        self.assertEqual(len(self.catalog), 0)

    def test_load_not_list_strict(self):
        with open(self.catalog_path, "w") as fh:
            json.dump({"not": "a list"}, fh)
        with self.assertRaises(CatalogValidationError):
            self.catalog.load(strict=True)

    def test_load_valid_catalog(self):
        with open(self.catalog_path, "w") as fh:
            json.dump([self.valid_asset_dict], fh)
        self.catalog.load()
        self.assertEqual(len(self.catalog), 1)
        loaded_asset = self.catalog.get("letter_A")
        self.assertIsNotNone(loaded_asset)
        self.assertEqual(loaded_asset.name, "Letter A")

    def test_load_skips_invalid_entries_non_strict(self):
        invalid_asset = self.valid_asset_dict.copy()
        del invalid_asset["name"]
        with open(self.catalog_path, "w") as fh:
            json.dump([self.valid_asset_dict, invalid_asset], fh)
        self.catalog.load(strict=False)
        self.assertEqual(len(self.catalog), 1)  # Only valid one loaded

    def test_load_raises_invalid_entries_strict(self):
        invalid_asset = self.valid_asset_dict.copy()
        del invalid_asset["name"]
        with open(self.catalog_path, "w") as fh:
            json.dump([self.valid_asset_dict, invalid_asset], fh)
        with self.assertRaises(CatalogValidationError):
            self.catalog.load(strict=True)

    # ── AssetCatalog.save tests ───────────────────────────────

    def test_save_catalog(self):
        self.catalog.add(self.valid_asset)
        self.catalog.save()

        self.assertTrue(os.path.exists(self.catalog_path))
        with open(self.catalog_path, "r") as fh:
            data = json.load(fh)

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "letter_A")

    @patch("pipeline.metadata.logger.error")
    def test_save_catalog_error(self, mock_logger):
        self.catalog.add(self.valid_asset)
        # Force an error by making directory unwritable, or patching open
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            self.catalog.save()
        mock_logger.assert_called_with("Failed to save catalog: %s", unittest.mock.ANY)

    # ── CRUD tests ────────────────────────────────────────────

    def test_add(self):
        self.catalog.add(self.valid_asset)
        self.assertEqual(len(self.catalog), 1)
        self.assertIn("letter_A", self.catalog._assets)

    def test_remove(self):
        self.catalog.add(self.valid_asset)

        # Remove existing
        self.assertTrue(self.catalog.remove("letter_A"))
        self.assertEqual(len(self.catalog), 0)

        # Remove non-existing
        self.assertFalse(self.catalog.remove("nonexistent"))

    def test_get(self):
        self.catalog.add(self.valid_asset)
        self.assertEqual(self.catalog.get("letter_A"), self.valid_asset)
        self.assertIsNone(self.catalog.get("nonexistent"))

    def test_all(self):
        self.catalog.add(self.valid_asset)
        all_assets = self.catalog.all()
        self.assertIsInstance(all_assets, list)
        self.assertEqual(len(all_assets), 1)
        self.assertEqual(all_assets[0], self.valid_asset)

    # ── Querying tests ────────────────────────────────────────

    def test_by_category(self):
        self.catalog.add(self.valid_asset)
        self.assertEqual(self.catalog.by_category(AssetCategory.LETTER), [self.valid_asset])
        self.assertEqual(self.catalog.by_category(AssetCategory.NUMBER), [])

    def test_by_theme(self):
        self.catalog.add(self.valid_asset)
        self.assertEqual(self.catalog.by_theme(AssetTheme.NEON), [self.valid_asset])
        self.assertEqual(self.catalog.by_theme(AssetTheme.CLOUD), [])

    def test_by_preset(self):
        self.catalog.add(self.valid_asset)

        # Asset has ["pulse", "glow"]
        self.assertEqual(self.catalog.by_preset("pulse"), [self.valid_asset])
        self.assertEqual(self.catalog.by_preset("sparkle"), [])

        # Asset with empty list is compatible with all
        asset2_dict = self.valid_asset_dict.copy()
        asset2_dict["id"] = "asset2"
        asset2_dict["animation_compatible_presets"] = []
        asset2 = Asset.from_dict(asset2_dict)
        self.catalog.add(asset2)

        self.assertIn(asset2, self.catalog.by_preset("pulse"))
        self.assertIn(asset2, self.catalog.by_preset("any_preset"))

    def test_search(self):
        self.catalog.add(self.valid_asset)

        # Case insensitive tag search
        self.assertEqual(self.catalog.search("ALPHABET"), [self.valid_asset])
        self.assertEqual(self.catalog.search("a"), [self.valid_asset])
        self.assertEqual(self.catalog.search("b"), [])

    def test_len_and_repr(self):
        self.assertEqual(len(self.catalog), 0)
        self.assertIn("count=0", repr(self.catalog))

        self.catalog.add(self.valid_asset)
        self.assertEqual(len(self.catalog), 1)
        self.assertIn("count=1", repr(self.catalog))

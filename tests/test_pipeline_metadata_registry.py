import os
import tempfile
import json
import unittest
from pathlib import Path

from pipeline.metadata.registry import AssetRegistry
from pipeline.asset_model.asset import Asset


class TestAssetRegistry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.source_dir = Path(self.temp_dir.name)

        # Valid asset 1
        asset1_data = {
            "id": "asset1",
            "name": "Asset 1",
            "category": "letter",
            "theme": "neon",
            "source_format": "png",
            "source_path": "letter/asset1.png",
            "width": 100,
            "height": 100,
            "tags": ["tag1", "tag2"],
            "animation_compatible_presets": ["preset1"],
            "export_targets": []
        }
        with open(self.source_dir / "asset1.json", "w") as f:
            json.dump(asset1_data, f)

        # Valid asset 2
        asset2_data = {
            "id": "asset2",
            "name": "Asset 2",
            "category": "number",
            "theme": "cloud",
            "source_format": "png",
            "source_path": "number/asset2.png",
            "width": 100,
            "height": 100,
            "tags": ["tag2", "tag3"],
            "animation_compatible_presets": [],
            "export_targets": []
        }
        with open(self.source_dir / "asset2.json", "w") as f:
            json.dump(asset2_data, f)

        # Invalid asset (should be logged and skipped)
        with open(self.source_dir / "invalid.json", "w") as f:
            f.write("invalid json")

        self.registry = AssetRegistry(source_dir=str(self.source_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load(self):
        self.assertEqual(len(self.registry), 2)

    def test_get(self):
        asset1 = self.registry.get("asset1")
        self.assertIsNotNone(asset1)
        self.assertEqual(asset1.id, "asset1")

        missing = self.registry.get("missing")
        self.assertIsNone(missing)

    def test_all(self):
        assets = self.registry.all()
        self.assertEqual(len(assets), 2)
        ids = {a.id for a in assets}
        self.assertEqual(ids, {"asset1", "asset2"})

    def test_get_by_category(self):
        letters = self.registry.get_by_category("letter")
        self.assertEqual(len(letters), 1)
        self.assertEqual(letters[0].id, "asset1")

        numbers = self.registry.get_by_category("number")
        self.assertEqual(len(numbers), 1)
        self.assertEqual(numbers[0].id, "asset2")

        missing = self.registry.get_by_category("missing")
        self.assertEqual(len(missing), 0)

    def test_get_by_theme(self):
        neons = self.registry.get_by_theme("neon")
        self.assertEqual(len(neons), 1)
        self.assertEqual(neons[0].id, "asset1")

        missing = self.registry.get_by_theme("missing")
        self.assertEqual(len(missing), 0)

    def test_get_by_tag(self):
        tag2s = self.registry.get_by_tag("tag2")
        self.assertEqual(len(tag2s), 2)

        tag1s = self.registry.get_by_tag("tag1")
        self.assertEqual(len(tag1s), 1)
        self.assertEqual(tag1s[0].id, "asset1")

        missing = self.registry.get_by_tag("missing")
        self.assertEqual(len(missing), 0)

    def test_get_compatible(self):
        preset1 = self.registry.get_compatible("preset1")
        self.assertEqual(len(preset1), 2)

        preset2 = self.registry.get_compatible("preset2")
        self.assertEqual(len(preset2), 1)
        self.assertEqual(preset2[0].id, "asset2")

    def test_register(self):
        asset3 = Asset(
            id="asset3",
            name="Asset 3",
            category="letter",
            theme="neon",
            source_format="png",
            source_path="letter/asset3.png",
            width=100,
            height=100
        )
        self.registry.register(asset3)
        self.assertEqual(len(self.registry), 3)
        self.assertEqual(self.registry.get("asset3").id, "asset3")

    def test_save(self):
        asset3 = Asset(
            id="asset3",
            name="Asset 3",
            category="letter",
            theme="neon",
            source_format="png",
            source_path="letter/asset3.png",
            width=100,
            height=100
        )
        path = self.registry.save(asset3)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(len(self.registry), 3)

        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["id"], "asset3")

    def test_reload(self):
        asset3_data = {
            "id": "asset3",
            "name": "Asset 3",
            "category": "letter",
            "theme": "neon",
            "source_format": "png",
            "source_path": "letter/asset3.png",
            "width": 100,
            "height": 100
        }
        with open(self.source_dir / "asset3.json", "w") as f:
            json.dump(asset3_data, f)

        self.assertEqual(len(self.registry), 2)
        self.registry.reload()
        self.assertEqual(len(self.registry), 3)

    def test_empty_source_dir(self):
        empty_registry = AssetRegistry(source_dir=str(self.source_dir / "nonexistent"))
        self.assertEqual(len(empty_registry), 0)

    def test_repr(self):
        r = repr(self.registry)
        self.assertIn("AssetRegistry assets=2", r)
        self.assertIn("source_dir=", r)

if __name__ == '__main__':
    unittest.main()

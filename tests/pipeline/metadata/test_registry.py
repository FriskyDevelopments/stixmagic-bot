import unittest
import json
import tempfile
import os
from pathlib import Path

from pipeline.metadata.registry import AssetRegistry
from pipeline.asset_model.asset import Asset, CATEGORY_LETTER, CATEGORY_EMOJI, THEME_NEON, THEME_CLOUD, FORMAT_PNG

class TestAssetRegistry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.source_dir = Path(self.temp_dir.name)

        # Create some test assets
        self.asset1 = Asset(
            id="letter_a_neon",
            name="Letter A",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="letters/letter_a_neon.png",
            width=512,
            height=512,
            tags=["letter", "neon", "red"],
            animation_compatible_presets=["pulse", "fade"]
        )

        self.asset2 = Asset(
            id="letter_b_neon",
            name="Letter B",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="letters/letter_b_neon.png",
            width=512,
            height=512,
            tags=["letter", "neon", "blue"],
            animation_compatible_presets=["pulse"]
        )

        self.asset3 = Asset(
            id="cloud_emoji",
            name="Cloud",
            category=CATEGORY_EMOJI,
            theme=THEME_CLOUD,
            source_format=FORMAT_PNG,
            source_path="emojis/cloud.png",
            width=512,
            height=512,
            tags=["cloud", "emoji", "weather"],
            animation_compatible_presets=[]
        )

        # Save to temp dir
        self._write_asset(self.asset1)
        self._write_asset(self.asset2)
        self._write_asset(self.asset3)

        self.registry = AssetRegistry(source_dir=str(self.source_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_asset(self, asset: Asset):
        cat_dir = self.source_dir / (asset.category + "s")
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / f"{asset.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asset.to_dict(), f)

    def test_get_existing_asset(self):
        asset = self.registry.get("letter_a_neon")
        self.assertIsNotNone(asset)
        self.assertEqual(asset.id, "letter_a_neon")
        self.assertEqual(asset.name, "Letter A")

    def test_get_nonexistent_asset(self):
        asset = self.registry.get("does_not_exist")
        self.assertIsNone(asset)

    def test_all(self):
        assets = self.registry.all()
        self.assertEqual(len(assets), 3)
        ids = [a.id for a in assets]
        self.assertIn("letter_a_neon", ids)
        self.assertIn("letter_b_neon", ids)
        self.assertIn("cloud_emoji", ids)

    def test_get_by_category(self):
        letters = self.registry.get_by_category(CATEGORY_LETTER)
        self.assertEqual(len(letters), 2)
        for a in letters:
            self.assertEqual(a.category, CATEGORY_LETTER)

        emojis = self.registry.get_by_category(CATEGORY_EMOJI)
        self.assertEqual(len(emojis), 1)
        self.assertEqual(emojis[0].category, CATEGORY_EMOJI)

        empty = self.registry.get_by_category("nonexistent")
        self.assertEqual(len(empty), 0)

    def test_get_by_theme(self):
        neon = self.registry.get_by_theme(THEME_NEON)
        self.assertEqual(len(neon), 2)
        for a in neon:
            self.assertEqual(a.theme, THEME_NEON)

        cloud = self.registry.get_by_theme(THEME_CLOUD)
        self.assertEqual(len(cloud), 1)
        self.assertEqual(cloud[0].theme, THEME_CLOUD)

        empty = self.registry.get_by_theme("nonexistent")
        self.assertEqual(len(empty), 0)

    def test_get_by_tag(self):
        neon = self.registry.get_by_tag("neon")
        self.assertEqual(len(neon), 2)

        blue = self.registry.get_by_tag("blue")
        self.assertEqual(len(blue), 1)
        self.assertEqual(blue[0].id, "letter_b_neon")

        empty = self.registry.get_by_tag("nonexistent")
        self.assertEqual(len(empty), 0)

    def test_get_compatible(self):
        pulse = self.registry.get_compatible("pulse")
        # asset1, asset2 have "pulse", asset3 has [] which means all are compatible
        self.assertEqual(len(pulse), 3)

        fade = self.registry.get_compatible("fade")
        # asset1 has "fade", asset3 has []
        self.assertEqual(len(fade), 2)
        ids = [a.id for a in fade]
        self.assertIn("letter_a_neon", ids)
        self.assertIn("cloud_emoji", ids)

        unknown = self.registry.get_compatible("unknown")
        # Only asset3 has []
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0].id, "cloud_emoji")

    def test_register(self):
        new_asset = Asset(
            id="new_asset",
            name="New",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="new.png",
            width=100,
            height=100
        )
        self.registry.register(new_asset)

        self.assertEqual(len(self.registry.all()), 4)
        fetched = self.registry.get("new_asset")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "New")

    def test_save(self):
        new_asset = Asset(
            id="save_test",
            name="Save Test",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="save.png",
            width=100,
            height=100
        )

        path = self.registry.save(new_asset)

        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data, new_asset.to_dict())

        # Test it's in registry
        self.assertIsNotNone(self.registry.get("save_test"))

    def test_reload(self):
        # Register in memory but not on disk
        new_asset = Asset(
            id="temp_asset",
            name="Temp",
            category=CATEGORY_LETTER,
            theme=THEME_NEON,
            source_format=FORMAT_PNG,
            source_path="temp.png",
            width=100,
            height=100
        )
        self.registry.register(new_asset)
        self.assertIsNotNone(self.registry.get("temp_asset"))

        # Reload from disk
        self.registry.reload()

        # temp_asset should be gone
        self.assertIsNone(self.registry.get("temp_asset"))
        # original 3 should remain
        self.assertEqual(len(self.registry.all()), 3)

    def test_load_with_invalid_json(self):
        # Create a malformed JSON file
        cat_dir = self.source_dir / "letters"
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / "bad.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ bad json ")

        # Should load valid files and ignore the bad one, logging an error
        registry = AssetRegistry(source_dir=str(self.source_dir))
        self.assertEqual(len(registry.all()), 3)

    def test_load_with_missing_dir(self):
        registry = AssetRegistry(source_dir=str(self.source_dir / "nonexistent"))
        self.assertEqual(len(registry.all()), 0)

    def test_len_and_repr(self):
        self.assertEqual(len(self.registry), 3)
        r = repr(self.registry)
        self.assertIn("AssetRegistry", r)
        self.assertIn("assets=3", r)

if __name__ == "__main__":
    unittest.main()

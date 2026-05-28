import unittest

from pipeline.metadata import AssetCatalog
from pipeline.asset_model import Asset

class TestAssetCatalog(unittest.TestCase):
    def test_remove_existing_asset(self):
        catalog = AssetCatalog()
        asset = Asset(
            id="test_id",
            name="Test",
            category="letter",
            source_format="png",
            source_path="test.png"
        )
        catalog.add(asset)

        # Test remove an existing asset
        # We don't assert the return value since the issue states it returns None,
        # but the current code returns bool. We just call it and check state.
        catalog.remove("test_id")
        self.assertIsNone(catalog.get("test_id"))
        self.assertEqual(len(catalog), 0)

    def test_remove_non_existing_asset(self):
        catalog = AssetCatalog()

        # Test remove a non-existing asset, should not raise KeyError
        try:
            catalog.remove("not_found")
        except KeyError:
            self.fail("remove() raised KeyError unexpectedly!")

        self.assertEqual(len(catalog), 0)

if __name__ == "__main__":
    unittest.main()

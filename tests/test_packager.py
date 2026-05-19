import unittest
from pipeline.packager import build_pack, PackDefinition, PackManifest, PackManifestEntry
from pipeline.asset_model import Asset

class MockCatalog:
    def __init__(self, assets):
        self._assets = {a.id: a for a in assets}

    def get(self, aid):
        return self._assets.get(aid)

    def all(self):
        return list(self._assets.values())

class TestPackager(unittest.TestCase):
    def test_build_pack(self):
        assets = [
            Asset(id="a1", name="A1", category="cat", source_format="png", source_path="p1"),
            Asset(id="a2", name="A2", category="cat", source_format="png", source_path="p2")
        ]
        catalog = MockCatalog(assets)

        pack = PackDefinition(
            pack_id="test_pack",
            title="Test Pack",
            included_assets=["a1"],
            export_formats=["gif", "thumbnail"],
            included_motion_presets=["preset1"]
        )

        import pipeline.motion_presets

        class MockPreset:
            def __init__(self, pid):
                self.id = pid

        pipeline.motion_presets.get_preset = lambda pid: MockPreset(pid)
        pipeline.motion_presets.BUILTIN_PRESETS = [MockPreset("builtin1")]
        pipeline.motion_presets.PRESET_REGISTRY = {"preset1": MockPreset("preset1")}

        manifest = build_pack(pack, catalog, strict_validation=False)
        self.assertEqual(manifest.pack_id, "test_pack")
        self.assertEqual(len(manifest.entries), 1)

        entry = manifest.entries[0]
        self.assertEqual(entry.asset_id, "a1")
        self.assertEqual(entry.preset_id, "preset1")
        self.assertTrue("thumbnail" in entry.expected_outputs)
        self.assertTrue("gif" in entry.expected_outputs)

if __name__ == '__main__':
    unittest.main()

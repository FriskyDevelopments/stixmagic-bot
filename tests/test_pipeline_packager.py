import unittest
from unittest.mock import MagicMock, patch

from pipeline.asset_model import Asset
from pipeline.packager import PackDefinition, PackManifestEntry
from pipeline.packager import _resolve_assets, _resolve_presets, _build_entries

class TestPipelinePackagerHelpers(unittest.TestCase):
    def test_resolve_assets_all(self):
        catalog_mock = MagicMock()
        asset1 = MagicMock(spec=Asset)
        asset1.id = "asset1"
        asset2 = MagicMock(spec=Asset)
        asset2.id = "asset2"
        catalog_mock.all.return_value = [asset1, asset2]

        pack = PackDefinition(pack_id="test_pack", title="Test Pack") # empty included_assets

        assets = _resolve_assets(pack, catalog_mock)
        self.assertEqual(len(assets), 2)
        self.assertEqual(assets[0].id, "asset1")
        self.assertEqual(assets[1].id, "asset2")
        catalog_mock.all.assert_called_once()
        catalog_mock.get.assert_not_called()

    def test_resolve_assets_subset(self):
        catalog_mock = MagicMock()
        asset1 = MagicMock(spec=Asset)
        asset1.id = "asset1"
        catalog_mock.get.side_effect = lambda aid: asset1 if aid == "asset1" else None

        pack = PackDefinition(pack_id="test_pack", title="Test Pack", included_assets=["asset1", "missing_asset"])

        assets = _resolve_assets(pack, catalog_mock)
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].id, "asset1")
        catalog_mock.all.assert_not_called()
        self.assertEqual(catalog_mock.get.call_count, 2)

    @patch("pipeline.packager.__init__.BUILTIN_PRESETS", create=True)
    def test_resolve_presets_all(self, builtin_presets_mock):
        preset_mock = MagicMock()
        preset_mock.id = "builtin_preset"
        builtin_presets_mock.__iter__.return_value = [preset_mock]

        pack = PackDefinition(pack_id="test_pack", title="Test Pack")

        with patch("pipeline.motion_presets.BUILTIN_PRESETS", [preset_mock]):
            presets = _resolve_presets(pack)
            self.assertEqual(len(presets), 1)
            self.assertEqual(presets[0].id, "builtin_preset")

    @patch("pipeline.packager.__init__.get_preset", create=True)
    def test_resolve_presets_subset(self, get_preset_mock):
        preset_mock = MagicMock()
        preset_mock.id = "preset1"
        get_preset_mock.side_effect = lambda pid: preset_mock if pid == "preset1" else None

        pack = PackDefinition(pack_id="test_pack", title="Test Pack", included_motion_presets=["preset1", "missing_preset"])

        with patch("pipeline.motion_presets.get_preset", side_effect=lambda pid: preset_mock if pid == "preset1" else None):
            presets = _resolve_presets(pack)
            self.assertEqual(len(presets), 1)
            self.assertEqual(presets[0].id, "preset1")

    def test_build_entries(self):
        pack = PackDefinition(
            pack_id="test_pack",
            title="Test Pack",
            export_formats=["gif", "png_sequence", "thumbnail", "webm"]
        )
        asset1 = MagicMock(spec=Asset)
        asset1.id = "asset1"

        preset_mock = MagicMock()
        preset_mock.id = "preset1"

        assets = [asset1]
        presets = [preset_mock]
        renders_root = "renders"

        entries = _build_entries(pack, assets, presets, renders_root)

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.asset_id, "asset1")
        self.assertEqual(entry.preset_id, "preset1")

        self.assertIn("gif", entry.expected_outputs)
        self.assertIn("webm", entry.expected_outputs)
        self.assertIn("thumbnail", entry.expected_outputs)
        self.assertIn("png_sequence", entry.expected_outputs)

        self.assertTrue(entry.expected_outputs["gif"].endswith("asset1_preset1.gif"))
        self.assertTrue(entry.expected_outputs["webm"].endswith("asset1_preset1.webm"))
        self.assertTrue(entry.expected_outputs["thumbnail"].endswith("asset1_thumb.png"))
        self.assertTrue(entry.expected_outputs["png_sequence"].endswith("asset1_preset1_frames"))

if __name__ == '__main__':
    unittest.main()

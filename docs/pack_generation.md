# Pack Generation

MagicStix packs are metadata-driven product bundles that group assets and
motion presets for a specific theme and target platform.

---

## Pack Definition Schema

Each pack is described by a `pack.json` file in `packs/<pack_id>/`:

| Field | Type | Description |
|---|---|---|
| `pack_id` | `string` | Unique slug (matches directory name) |
| `title` | `string` | Human-readable pack title |
| `theme` | `string` | Stylistic theme |
| `included_assets` | `string[]` | Asset IDs to include (empty = all) |
| `included_motion_presets` | `string[]` | Preset IDs to apply (empty = all) |
| `export_formats` | `string[]` | Formats to produce |
| `target_platforms` | `string[]` | Where assets will be used |
| `use_cases` | `string[]` | Description of intended use |
| `notes` | `string` | Free-form remarks |

---

## Available Packs

| Pack ID | Title | Theme |
|---|---|---|
| `motion_alphabet` | MagicStix Motion Alphabet | neon |
| `neon_signals` | MagicStix Neon Signals | neon |
| `dj_pack` | MagicStix DJ Pack | dj |
| `cloud_pack` | MagicStix Cloud Pack | cloud |
| `overlay_starter` | MagicStix Overlay Starter Pack | abstract |

---

## Building a Pack Manifest

`build_pack()` resolves all assets and presets for a pack and returns the
expected output paths, without running the exporters:

```python
from pipeline.packager import PackDefinition, build_pack
from pipeline.metadata import AssetCatalog

catalog = AssetCatalog(auto_load=True)
pack    = PackDefinition.from_file("packs/motion_alphabet/pack.json")
manifest = build_pack(pack, catalog)

print(manifest.summary())
# Pack 'motion_alphabet': 36 asset×preset combinations, 144 total expected output files.

for entry in manifest.entries[:3]:
    print(entry.asset_id, entry.preset_id, entry.expected_outputs)
```

---

## Running a Full Pack Export

```python
from pipeline.packager import PackDefinition, build_pack
from pipeline.metadata import AssetCatalog
from pipeline.exporters import export_all
from pipeline.motion_presets import get_preset

catalog  = AssetCatalog(auto_load=True)
pack     = PackDefinition.from_file("packs/motion_alphabet/pack.json")
manifest = build_pack(pack, catalog)

for entry in manifest.entries:
    asset  = catalog.get(entry.asset_id)
    preset = get_preset(entry.preset_id)
    result = export_all(
        asset_id     = asset.id,
        source_path  = asset.source_path,
        preset       = preset,
        renders_root = "renders",
        formats      = pack.export_formats,
    )
    if result.errors:
        print(f"Errors for {asset.id}+{preset.id}: {result.errors}")
```

---

## Creating a New Pack

1. Create a directory: `packs/<pack_id>/`
2. Write a `pack.json` using the schema above.
3. Optionally populate `included_assets` with specific asset IDs.
   Leave empty to include all catalog assets.
4. Run `build_pack()` to verify the manifest before exporting.

---

## Pack Metadata Principle

Pack contents are **never** hardcoded in Python source.  All pack membership
is declared in `pack.json` and resolved at runtime from the asset catalog.
This allows packs to be updated by editing JSON without touching code.

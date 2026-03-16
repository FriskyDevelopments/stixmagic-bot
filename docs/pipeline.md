# MagicStix Pipeline

## Purpose

The pipeline transforms base assets (produced by the bot or sourced externally)
into multiple export formats using reusable motion presets.

---

## Entry Point

```python
from pipeline.metadata import AssetCatalog
from pipeline.motion_presets import get_preset
from pipeline.exporters import export_all

catalog = AssetCatalog(auto_load=True)
asset   = catalog.get("letter_A")
preset  = get_preset("pulse")

result  = export_all(
    asset_id    = asset.id,
    source_path = asset.source_path,
    preset      = preset,
    renders_root= "renders",
    formats     = ["gif", "webp", "webm", "thumbnail"],
)

print(result.sticker_ready_outputs)
print(result.overlay_ready_outputs)
print(result.preview_outputs)
```

---

## Pipeline Flow

```
Bot or external tool
       │
       ▼
assets/source/<category>/<asset_file>
       │
       ▼
pipeline/asset_model  ← Asset dataclass
       │
       ▼
pipeline/metadata     ← AssetCatalog (assets/catalog.json)
       │
       ▼
pipeline/motion_presets ← select MotionPreset(s)
       │
       ▼
pipeline/exporters    ← export_all() runs per-format drivers
       │
       ├── renders/gif/       ← .gif
       ├── renders/webp/      ← .webp (animated)
       ├── renders/webm/      ← .webm (VP9 + alpha)
       ├── renders/mov/       ← .mov (ProRes 4444 + alpha)
       ├── renders/png_sequences/ ← numbered PNG frames
       └── renders/thumbnails/    ← preview PNG
              │
              ▼
pipeline/packager  ← build_pack() groups outputs into a pack manifest
```

---

## Adding a New Asset

1. Drop the source file into `assets/source/<category>/`.
2. Create an `Asset` record and add it to the catalog:

```python
from pipeline.asset_model import Asset, AssetCategory, SourceFormat
from pipeline.metadata import AssetCatalog

catalog = AssetCatalog(auto_load=True)
catalog.add(Asset(
    id="letter_A",
    name="Letter A",
    category=AssetCategory.LETTER,
    source_format=SourceFormat.PNG,
    source_path="assets/source/letters/A.png",
    tags=["alphabet", "neon"],
))
catalog.save()
```

3. Run the exporter:

```python
from pipeline.motion_presets import get_preset
from pipeline.exporters import export_all

result = export_all("letter_A", "assets/source/letters/A.png", get_preset("pulse"))
```

---

## Adding a New Motion Preset

Add a `MotionPreset` entry to the `BUILTIN_PRESETS` list in
`pipeline/motion_presets/__init__.py`.

The preset will automatically be available to all exporters and pack builders.

---

## Implementing an Exporter

Each unimplemented exporter in `pipeline/exporters/__init__.py` has a
`# TODO:` comment describing what needs to be built.  Replace the
`_write_placeholder()` call with real rendering logic.

Example for GIF:

```python
def export_gif(source_path, preset, output_dir, **kwargs):
    # Real implementation using Pillow
    frames = render_frames(source_path, preset)
    out_path = os.path.join(output_dir, ...)
    frames[0].save(out_path, save_all=True, append_images=frames[1:], loop=0)
    return out_path
```

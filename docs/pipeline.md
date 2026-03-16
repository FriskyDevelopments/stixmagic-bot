# MagicStix — Pipeline Walkthrough

> **Layer 2–5 implementation guide**

This document explains how to use the MagicStix visual asset pipeline to
transform a base asset into multiple export formats.

---

## Quick Start

```python
from pipeline.metadata.registry import AssetRegistry
from pipeline.motion_presets.catalog import PRESETS, get_preset
from pipeline.exporters.gif_exporter import GifExporter
from pipeline.packager.generator import PackGenerator

# 1. Load the asset registry
registry = AssetRegistry()          # scans assets/source/**/*.json

# 2. Look up an asset and a preset
asset  = registry.get("letter_a_neon")
preset = get_preset("pulse")

# 3. Export one format
exporter = GifExporter()
result   = exporter.export(asset, preset)
print(result.path, result.success)  # renders/gif/letter_a_neon_pulse.gif

# 4. Generate a whole pack
generator = PackGenerator(registry)
results   = generator.generate("motion_alphabet")
for r in results:
    print(f"[{'OK' if r.success else 'FAIL'}] {r.format}: {r.path}")
```

---

## Step-by-Step Pipeline

### Step 1 — Register a base asset

Create a JSON descriptor file under `assets/source/<category>/`:

```json
// assets/source/letters/letter_a_neon.json
{
  "id": "letter_a_neon",
  "name": "Letter A (Neon)",
  "category": "letter",
  "theme": "neon",
  "source_format": "png",
  "source_path": "assets/source/letters/letter_a_neon.png",
  "width": 512,
  "height": 512,
  "transparent_background": true,
  "tags": ["alphabet", "neon", "uppercase"],
  "animation_compatible_presets": [],
  "export_targets": ["gif", "webp", "webm", "thumbnails"],
  "notes": ""
}
```

The `AssetRegistry` will pick this up automatically on the next start (or
after calling `registry.reload()`).

Alternatively, register programmatically:

```python
from pipeline.asset_model.asset import Asset
from pipeline.metadata.registry import AssetRegistry

registry = AssetRegistry()
asset = Asset(
    id="letter_a_neon",
    name="Letter A (Neon)",
    category="letter",
    theme="neon",
    source_format="png",
    source_path="assets/source/letters/letter_a_neon.png",
    width=512,
    height=512,
)
registry.save(asset)   # writes JSON + adds to in-memory registry
```

---

### Step 2 — Choose a motion preset

```python
from pipeline.motion_presets.catalog import PRESETS, list_presets

# List all available presets
for preset in list_presets():
    print(preset.id, "—", preset.description[:60])

# Use a specific preset
pulse = PRESETS["pulse"]
print(pulse.parameter_schema)
```

Available built-in presets:

| ID | Name | Loop | Duration |
|---|---|---|---|
| `pulse` | Pulse | ✓ | 800 ms |
| `glow` | Glow | ✓ | 1200 ms |
| `wobble` | Wobble | ✓ | 600 ms |
| `bounce` | Bounce | ✓ | 700 ms |
| `orbit` | Orbit | ✓ | 2000 ms |
| `glitch` | Glitch | ✓ | 500 ms |
| `sparkle` | Sparkle | ✓ | 1500 ms |
| `particle_burst` | Particle Burst | ✗ | 1000 ms |
| `laser_sweep` | Laser Sweep | ✓ | 1000 ms |
| `signal_flash` | Signal Flash | ✓ | 400 ms |

---

### Step 3 — Export to a specific format

Each exporter inherits from `BaseExporter` and implements `export(asset, preset)`.

```python
from pipeline.exporters.gif_exporter       import GifExporter
from pipeline.exporters.webp_exporter      import AnimatedWebpExporter
from pipeline.exporters.webm_exporter      import WebmExporter
from pipeline.exporters.mov_exporter       import MovExporter
from pipeline.exporters.png_sequence_exporter import PngSequenceExporter
from pipeline.exporters.thumbnail_exporter import ThumbnailExporter

exporters = [
    GifExporter(),
    AnimatedWebpExporter(),
    WebmExporter(),
    MovExporter(),
    PngSequenceExporter(),
    ThumbnailExporter(),
]

for exp in exporters:
    result = exp.export(asset, preset)
    print(result)
```

Output files are written to:

```
renders/
├── gif/         letter_a_neon_pulse.gif
├── webp/        letter_a_neon_pulse.webp
├── webm/        letter_a_neon_pulse.webm
├── mov/         letter_a_neon_pulse.mov
├── png_sequences/letter_a_neon_pulse/frame0000.png …
└── thumbnails/  letter_a_neon_pulse_preview.jpg
```

---

### Step 4 — Generate a product pack

Pack descriptors live in `packs/<pack_id>/pack.json`.  The `PackGenerator`
reads the descriptor, resolves assets and presets, and runs all exporters.

```python
from pipeline.metadata.registry import AssetRegistry
from pipeline.packager.generator import PackGenerator

registry  = AssetRegistry()
generator = PackGenerator(registry)

# Generate one pack
results = generator.generate("motion_alphabet")

# Generate all packs
all_results = generator.generate_all()
for pack_id, pack_results in all_results.items():
    ok  = sum(1 for r in pack_results if r.success)
    err = sum(1 for r in pack_results if not r.success)
    print(f"{pack_id}: {ok} ok, {err} failed")
```

---

## Output Classification

The pipeline distinguishes three output classes:

| Class | Formats | Use |
|---|---|---|
| **Sticker-ready** | GIF, animated WebP | Telegram sticker packs |
| **Overlay-ready** | WebM + alpha, MOV + alpha | OBS, compositor, virtual camera |
| **Preview** | JPEG thumbnail | Catalog listings, pack covers |

Pack descriptors specify which classes to produce via `export_formats`.

---

## Adding a New Exporter

1. Create `pipeline/exporters/my_format_exporter.py`.
2. Subclass `BaseExporter`, set `format_id = "my_format"`.
3. Implement `export(self, asset, preset) -> ExportResult`.
4. Add the class to `pipeline/exporters/__init__.py`.
5. Add the format string to `_EXPORTERS` in `pipeline/packager/generator.py`.
6. Document the format in `docs/export_formats.md`.

---

## Adding a New Motion Preset

1. Instantiate a `MotionPreset` in `pipeline/motion_presets/catalog.py`.
2. Add it to the `PRESETS` dict.
3. Implement the visual effect in each relevant exporter's `_render_frames` /
   `_render` method.
4. Document the preset in `docs/motion_system.md`.

# Export Formats

The MagicStix export pipeline produces multiple output formats from a single
base asset + motion preset combination.

---

## Supported Formats

| Format | Extension | Status | Use Case |
|---|---|---|---|
| Animated GIF | `.gif` | 🚧 Placeholder | Telegram stickers, web previews |
| Animated WebP | `.webp` | 🚧 Placeholder | Telegram animated stickers, modern web |
| VP9 WebM + alpha | `.webm` | 🚧 Placeholder | Overlay compositor, OBS sources |
| ProRes 4444 MOV + alpha | `.mov` | 🚧 Placeholder | Professional overlay compositing |
| PNG frame sequence | `_frames/` | 🚧 Placeholder | Offline compositing, After Effects |
| Preview thumbnail | `.png` | ✅ Implemented | Pack previews, catalog thumbnails |

---

## Output Classification

### sticker_ready_outputs

Formats appropriate for Telegram stickers:

- `gif`
- `webp`
- `webm`

### overlay_ready_outputs

Formats with preserved alpha channel for compositor use:

- `webm`
- `mov`

### preview_outputs

- `thumbnail`

---

## Output Naming Convention

Output files follow the pattern:

```
<asset_id>_<preset_id>.<ext>
```

Examples:

```
letter_A_pulse.gif
letter_A_pulse.webp
symbol_cloud_sparkle.webm
signal_hand_glow_thumb.png
```

---

## Running Exports

```python
from pipeline.metadata import AssetCatalog
from pipeline.motion_presets import get_preset
from pipeline.exporters import export_all

catalog = AssetCatalog(auto_load=True)
asset   = catalog.get("letter_A")
preset  = get_preset("pulse")

result = export_all(
    asset_id     = asset.id,
    source_path  = asset.source_path,
    preset       = preset,
    renders_root = "renders",
    formats      = ["gif", "webp", "webm", "thumbnail"],
)

print(result.sticker_ready_outputs)
# {'gif': 'renders/gif/letter_A_pulse.gif',
#  'webp': 'renders/webp/letter_A_pulse.webp',
#  'webm': 'renders/webm/letter_A_pulse.webm'}

print(result.errors)
# [] (or list of any errors)
```

---

## Implementing an Exporter

Each placeholder exporter writes a `.txt` stub file and logs a `WARNING`.
To implement a real exporter, replace the `_write_placeholder()` call with
actual rendering logic.  See [`docs/pipeline.md`](pipeline.md) for a code
example.

---

## Format Constraints

### Telegram Stickers

- Animated stickers must loop
- WebM: VP9 codec, yuva420p pixel format, max 3 s, max 512 px, ≤ 256 KB
- Static WebP: RGBA, max 512 px, ≤ 64 KB

### OBS/Compositor Overlays

- Must have genuine alpha channel (not keyed green-screen)
- Preferred: WebM VP9 or MOV ProRes 4444 with alpha
- Resolution: match stream resolution (720p or 1080p)

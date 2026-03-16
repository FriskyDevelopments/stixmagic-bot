# MagicStix — Asset JSON Schema

Every base asset in the MagicStix pipeline is described by a JSON file stored
under `assets/source/<category>/`.  This document defines the schema for those
files and maps each field to the `Asset` Python dataclass.

---

## Schema

```json
{
  "id":                           "letter_a_neon",
  "name":                         "Letter A (Neon)",
  "category":                     "letter",
  "theme":                        "neon",
  "source_format":                "png",
  "source_path":                  "assets/source/letters/letter_a_neon.png",
  "width":                        512,
  "height":                       512,
  "transparent_background":       true,
  "tags":                         ["alphabet", "neon", "uppercase"],
  "animation_compatible_presets": [],
  "export_targets":               ["gif", "webp", "webm", "thumbnails"],
  "notes":                        ""
}
```

---

## Field Reference

### `id` *(string, required)*

Unique identifier for the asset.  Used as the primary key in the
`AssetRegistry` and as part of output file names.

Convention: `<category>_<name>_<theme>` using snake_case.

Examples: `letter_a_neon`, `cloud_symbol_abstract`, `wifi_signal_neon`.

---

### `name` *(string, required)*

Human-readable display name shown in pack listings and the Mini App catalog.

---

### `category` *(string, required)*

Asset category.  Must be one of:

| Value | Description |
|---|---|
| `letter` | Alphabetic character (A–Z, a–z) |
| `number` | Numeric digit (0–9) |
| `emoji` | Emoji-style graphic |
| `signal` | Signal indicator (WiFi, radio, etc.) |
| `frame` | Decorative border or frame |
| `particle` | Small decorative particle element |
| `icon` | Generic icon or pictogram |
| `sticker` | Telegram-ready sticker asset |
| `overlay_element` | Overlay-specific element (safe for compositor) |
| `symbol` | Abstract symbol or shape |

---

### `theme` *(string, required)*

Visual theme of the asset.  Must be one of:

| Value | Description |
|---|---|
| `neon` | Bright neon-lit style |
| `cloud` | Sky / cloud / weather motifs |
| `signal` | Data / radio / transmission signals |
| `dj` | DJ / music / club night |
| `club` | Nightclub / party atmosphere |
| `host` | Hosting / broadcast |
| `trading` | Finance / trading / charts |
| `abstract` | Generic / mixed-use |

---

### `source_format` *(string, required)*

File format of the source asset file:

| Value | Description |
|---|---|
| `png` | Raster PNG (RGBA recommended) |
| `svg` | Vector SVG (future support) |
| `webp` | WEBP (Telegram-native) |

---

### `source_path` *(string, required)*

Relative path to the source file from the repository root.

Convention: `assets/source/<category>s/<id>.<ext>`

---

### `width` / `height` *(integer, required)*

Source image dimensions in pixels.  Standard sizes: 512×512 or 256×256.

---

### `transparent_background` *(boolean, default: true)*

Set to `true` when the source image has a transparent (alpha) background.
Exporters use this flag to decide whether to composite over a background fill.

---

### `tags` *(array of strings, default: [])*

Free-form tags for search and grouping.  Examples: `["uppercase", "neon", "A"]`.

---

### `animation_compatible_presets` *(array of strings, default: [])*

IDs of motion presets that have been tested and work well with this asset.
An empty array means **all presets** are considered compatible.

To restrict an asset to specific presets:

```json
"animation_compatible_presets": ["pulse", "glow"]
```

---

### `export_targets` *(array of strings, default: [])*

Output formats to generate for this asset.  An empty array means **all formats**
configured in the pack are enabled.

Valid values: `gif`, `webp`, `webm`, `mov`, `png_sequences`, `thumbnails`.

---

### `notes` *(string, default: "")*

Free-form notes for pipeline operators.  Not shown to end-users.

---

## File Naming Convention

```
assets/source/<category>s/<asset_id>.<ext>
assets/source/<category>s/<asset_id>.json
```

Example:

```
assets/source/letters/letter_a_neon.png
assets/source/letters/letter_a_neon.json
```

The JSON descriptor and the source image must share the same base name.

---

## Validation

The `AssetRegistry` logs errors and skips any JSON file that cannot be
parsed as a valid `Asset`.  Run the following snippet to validate all
descriptors on disk:

```python
from pipeline.metadata.registry import AssetRegistry
import logging
logging.basicConfig(level=logging.DEBUG)
registry = AssetRegistry()
print(f"Loaded {len(registry)} asset(s)")
```

Any `ERROR` log lines indicate invalid descriptor files.

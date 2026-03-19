# Asset Schema

All base assets are described by the `Asset` dataclass in
`pipeline/asset_model/__init__.py`.  The on-disk representation is a JSON
array stored in `assets/catalog.json`.

---

## Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | ✅ | Unique slug, e.g. `"letter_A"` |
| `name` | `string` | ✅ | Human-readable label |
| `category` | `string` (enum) | ✅ | See [Categories](#categories) |
| `source_format` | `string` (enum) | ✅ | `png`, `svg`, `webp`, `gif`, `webm` |
| `source_path` | `string` | ✅ | Path to source file relative to repo root |
| `width` | `integer` | — | Native width in pixels (default: 512) |
| `height` | `integer` | — | Native height in pixels (default: 512) |
| `transparent_background` | `boolean` | — | Has alpha channel (default: `true`) |
| `theme` | `string` (enum) | — | See [Themes](#themes) |
| `tags` | `string[]` | — | Free-form keyword list |
| `animation_compatible_presets` | `string[]` | — | Preset IDs; empty = all presets allowed |
| `export_targets` | `string[]` | — | Override export formats; empty = pack default |
| `notes` | `string` | — | Free-form remarks |

---

## Categories

| Value | Description |
|---|---|
| `letter` | Alphabet character |
| `number` | Digit 0–9 |
| `emoji` | Emoji-style face or reaction |
| `signal` | Signal or indicator icon |
| `frame` | Border or frame element |
| `particle` | Small decorative particle |
| `icon` | General icon |
| `sticker` | Complete sticker (not a base element) |
| `overlay_element` | Designed for compositor overlay use |
| `symbol` | Abstract symbol or shape |

---

## Themes

| Value | Description |
|---|---|
| `neon` | Neon glow aesthetic |
| `cloud` | Cloud / atmospheric aesthetic |
| `signal` | Technical signal / indicator aesthetic |
| `dj` | DJ / music event aesthetic |
| `club` | Night club aesthetic |
| `host` | Host / presenter aesthetic |
| `trading` | Financial / trading aesthetic |
| `abstract` | No specific theme |

---

## Example Record

```json
{
  "id": "letter_A",
  "name": "Letter A",
  "category": "letter",
  "source_format": "png",
  "source_path": "assets/source/letters/A.png",
  "width": 512,
  "height": 512,
  "transparent_background": true,
  "theme": "neon",
  "tags": ["alphabet", "neon", "uppercase"],
  "animation_compatible_presets": ["pulse", "glow", "glitch"],
  "export_targets": [],
  "notes": ""
}
```

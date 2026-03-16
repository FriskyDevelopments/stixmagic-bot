# MagicStix — Pack Generation Guide

Product packs group base assets and motion presets together and describe which
export formats to produce and which platforms to target.  Pack generation is
entirely metadata-driven — no hardcoded file lists.

---

## Pack Descriptor Schema

Each pack is described by a `pack.json` file under `packs/<pack_id>/`:

```json
{
  "pack_id":                "motion_alphabet",
  "title":                  "MagicStix Motion Alphabet",
  "theme":                  "neon",
  "description":            "Animated neon letters A–Z …",
  "included_assets":        ["letter_a_neon", "letter_b_neon"],
  "included_motion_presets":["pulse", "glow"],
  "export_formats":         ["gif", "webp", "webm", "thumbnails"],
  "target_platforms":       ["telegram", "overlay"],
  "use_cases":              ["sticker", "animated_alphabet"]
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `pack_id` | string | Unique identifier — must match the directory name |
| `title` | string | Human-readable display title |
| `theme` | string | Visual theme (`neon`, `cloud`, `dj`, `abstract`, …) |
| `description` | string | What this pack is for |
| `included_assets` | array | Asset IDs to include (from the `AssetRegistry`) |
| `included_motion_presets` | array | Preset IDs to apply to every asset |
| `export_formats` | array | Target formats (`gif`, `webp`, `webm`, `mov`, `png_sequences`, `thumbnails`) |
| `target_platforms` | array | Deployment targets (`telegram`, `overlay`, `virtual_camera`, `browser_extension`) |
| `use_cases` | array | High-level labels (`sticker`, `stream_overlay`, etc.) |

---

## Running the Pack Generator

```python
from pipeline.metadata.registry import AssetRegistry
from pipeline.packager.generator import PackGenerator

registry  = AssetRegistry()
generator = PackGenerator(registry)

# Generate one pack
results = generator.generate("motion_alphabet")
for r in results:
    status = "✓" if r.success else "✗"
    print(f"  [{status}] {r.format}: {r.path}")

# Generate ALL packs
all_results = generator.generate_all()
for pack_id, pack_results in all_results.items():
    ok  = sum(1 for r in pack_results if r.success)
    err = sum(1 for r in pack_results if not r.success)
    print(f"{pack_id}: {ok} ok, {err} failed")
```

---

## Pre-defined Packs

### `motion_alphabet` — MagicStix Motion Alphabet

Animated neon letters A–Z with pulse, glow, and glitch effects.

- **Theme:** neon
- **Presets:** pulse, glow, glitch
- **Formats:** gif, webp, webm, thumbnails
- **Platforms:** telegram, overlay, virtual_camera

### `neon_signals` — MagicStix Neon Signals

Neon signal icons (WiFi, radio waves, arrows) with laser sweep and signal flash.

- **Theme:** neon
- **Presets:** laser_sweep, signal_flash, glow
- **Formats:** gif, webp, webm, mov, thumbnails
- **Platforms:** telegram, overlay, browser_extension

### `dj_pack` — MagicStix DJ Pack

DJ-themed animated icons with bounce, pulse, and laser effects.

- **Theme:** dj
- **Presets:** bounce, pulse, laser_sweep
- **Formats:** gif, webp, webm, thumbnails
- **Platforms:** telegram, overlay, virtual_camera

### `cloud_pack` — MagicStix Cloud Pack

Cloud and sky motifs with orbit, sparkle, and wobble effects.

- **Theme:** cloud
- **Presets:** orbit, sparkle, wobble
- **Formats:** gif, webp, webm, thumbnails
- **Platforms:** telegram, browser_extension

### `overlay_starter` — MagicStix Overlay Starter Pack

Overlay-safe animated elements for OBS and virtual camera setups.

- **Theme:** abstract
- **Presets:** pulse, particle_burst, glow, laser_sweep
- **Formats:** webm, mov, png_sequences, thumbnails
- **Platforms:** overlay, virtual_camera, obs

---

## Adding a New Pack

1. Create the directory: `packs/<pack_id>/`
2. Write `packs/<pack_id>/pack.json` following the schema above.
3. Add the asset IDs to `included_assets` (they must be registered in the `AssetRegistry`).
4. Choose presets from the [motion preset catalog](motion_system.md).
5. Run `PackGenerator.generate("<pack_id>")` to test.

---

## Generation Output Structure

For a pack with 26 letter assets × 3 presets × 4 export formats, the generator
will attempt to write 312 files:

```
renders/
├── gif/
│   ├── letter_a_neon_pulse.gif
│   ├── letter_a_neon_glow.gif
│   ├── letter_a_neon_glitch.gif
│   ├── letter_b_neon_pulse.gif
│   └── …
├── webp/        (same structure)
├── webm/        (same structure)
└── thumbnails/
    ├── letter_a_neon_pulse_preview.jpg
    └── …
```

---

## Selective Export via `animation_compatible_presets`

If an asset's JSON descriptor restricts `animation_compatible_presets`, the
generator automatically skips incompatible (asset, preset) pairs:

```json
{
  "id": "wifi_signal",
  "animation_compatible_presets": ["signal_flash", "laser_sweep"]
}
```

With this descriptor, applying `pulse` to `wifi_signal` will be silently
skipped even if `pulse` appears in the pack's `included_motion_presets`.

---

## Selective Export via `export_targets`

Similarly, an asset can restrict which output formats it produces:

```json
{
  "id": "overlay_frame_01",
  "export_targets": ["webm", "mov", "thumbnails"]
}
```

This overrides the pack's `export_formats` for this specific asset.
*(Note: asset-level `export_targets` filtering is implemented in the `Asset`
dataclass but the `PackGenerator` currently uses the pack-level
`export_formats` only.  Asset-level filtering can be added in a future sprint.)*

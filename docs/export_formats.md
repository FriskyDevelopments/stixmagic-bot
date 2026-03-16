# MagicStix — Export Formats

The MagicStix export pipeline produces six output formats from every
(asset, motion preset) pair.  This document describes each format,
its use cases, file size targets, and implementation status.

---

## Format Overview

| Format | File Ext | Alpha | Loop | Use Case | Status |
|---|---|---|---|---|---|
| Animated GIF | `.gif` | ✗ | ✓ | Telegram sticker, chat | Placeholder |
| Animated WebP | `.webp` | ✓ | ✓ | Telegram sticker, web | Placeholder |
| WebM + alpha | `.webm` | ✓ | ✓ | Overlay, virtual camera | Placeholder |
| MOV + alpha | `.mov` | ✓ | ✓ | OBS, After Effects | Placeholder |
| PNG sequence | dir of `.png` | ✓ | N/A | Intermediate / lossless | Placeholder |
| JPEG thumbnail | `.jpg` | ✗ | N/A | Catalog preview | Placeholder |

> All exporters currently write **stub/placeholder files**.  Replace the
> `_render_frames` / `_render` / `_render_thumbnail` methods with real
> Pillow / ffmpeg rendering code.

---

## Output Directory Structure

```
renders/
├── gif/                    <asset_id>_<preset_id>.gif
├── webp/                   <asset_id>_<preset_id>.webp
├── webm/                   <asset_id>_<preset_id>.webm
├── mov/                    <asset_id>_<preset_id>.mov
├── png_sequences/
│   └── <asset_id>_<preset_id>/
│       ├── frame0000.png
│       ├── frame0001.png
│       └── …
└── thumbnails/             <asset_id>_<preset_id>_preview.jpg
```

---

## GIF — Animated GIF

**Exporter:** `pipeline/exporters/gif_exporter.py`  
**Format ID:** `gif`

- **Alpha channel:** No (255/0 binary transparency only via `transparency` palette index)
- **Loop:** Looped via `loop=0` in Pillow
- **Max file size target:** ≤ 256 KB for Telegram compatibility
- **Frame rate:** 25–30 fps recommended

Implementation notes:
- Compose frames with Pillow `Image` objects.
- Use `img.save(path, format='GIF', save_all=True, append_images=frames, loop=0, duration=frame_ms)`.
- Dither to 256-colour palette: `img.quantize(colors=256, method=Image.MEDIANCUT)`.

---

## Animated WebP

**Exporter:** `pipeline/exporters/webp_exporter.py`  
**Format ID:** `webp`

- **Alpha channel:** Yes (full RGBA)
- **Loop:** Looped via `loop=0`
- **Max file size target:** ≤ 256 KB for Telegram animated sticker
- **Pillow version required:** ≥ 3.4 for animated WebP write support

Implementation notes:
- Same frame composition as GIF but save as WebP for better alpha support.
- `img.save(path, format='WEBP', save_all=True, append_images=frames, loop=0, duration=frame_ms)`.

---

## WebM + Alpha

**Exporter:** `pipeline/exporters/webm_exporter.py`  
**Format ID:** `webm`

- **Alpha channel:** Yes (via VP9 `yuva420p` pixel format)
- **Loop:** Infinite (set by player; no explicit loop in container)
- **Max file size target:** ≤ 256 KB (Telegram); unconstrained for overlay use
- **Codec:** `libvpx-vp9`

Implementation notes:
- Pipe PNG frames via stdin using `image2pipe` demuxer.
- ffmpeg command:
  ```
  ffmpeg -f image2pipe -vcodec png -r 30 -i pipe:0 \
      -c:v libvpx-vp9 -b:v 200k -t 3 -an -pix_fmt yuva420p output.webm
  ```
- Re-use `_run_ffmpeg` from `domain/media.py` for consistency.

---

## MOV + Alpha

**Exporter:** `pipeline/exporters/mov_exporter.py`  
**Format ID:** `mov`

- **Alpha channel:** Yes (ProRes 4444 `yuva444p10le` or QTRLE)
- **Use case:** OBS, After Effects, Premiere Pro, virtual camera overlay
- **Codec:** `prores_ks -profile:v 4444` (preferred) or `qtrle`

Implementation notes:
- ffmpeg command (ProRes 4444):
  ```
  ffmpeg -f image2pipe -vcodec png -r 30 -i pipe:0 \
      -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le output.mov
  ```
- Note: ProRes 4444 files are significantly larger than WebM; target ≤ 5 MB.

---

## PNG Sequence

**Exporter:** `pipeline/exporters/png_sequence_exporter.py`  
**Format ID:** `png_sequences`

- **Alpha channel:** Yes (full RGBA)
- **Use case:** Lossless intermediate for video encoders; After Effects import
- **Output:** Directory of zero-padded numbered files (`frame0000.png`, …)

Implementation notes:
- Each frame is a 512×512 RGBA Pillow image saved as PNG.
- Frame count = `ceil(preset.duration_ms / (1000 / fps))`.
- The directory path (not a file) is returned as `ExportResult.path`.

---

## JPEG Thumbnail

**Exporter:** `pipeline/exporters/thumbnail_exporter.py`  
**Format ID:** `thumbnails`

- **Alpha channel:** No (JPEG)
- **Size:** 256×256 px (centred on white or dark background)
- **Quality:** JPEG quality 85
- **Use case:** Pack listings, Mini App catalog, asset documentation

Implementation notes:
- Open the source asset with Pillow.
- Optionally apply the first frame of the motion preset.
- Composite onto a 256×256 canvas (transparent → dark background for dark themes).
- Save as JPEG quality 85.

---

## Output Classification

Outputs are grouped into three classes to simplify pack configuration:

### Sticker-ready outputs
Suitable for Telegram sticker packs:
- `gif`
- `webp`

### Overlay-ready outputs
Suitable for OBS, compositor, virtual camera:
- `webm`
- `mov`
- `png_sequences`

### Preview outputs
Suitable for catalog listings and pack covers:
- `thumbnails`

Pack descriptors use the `export_formats` list to specify which classes to
generate.  See [`pack_generation.md`](pack_generation.md) for examples.

# MagicStix — Motion Preset System

Motion presets are reusable, parameterised animation descriptors.
They define *what* an animation effect should look like and *which assets* it
works best with — but they do not contain rendering code.
Rendering is handled by the exporter layer.

---

## Design Goals

- **Reusable across asset categories** — `pulse` works on a letter, an emoji, and a symbol.
- **Parameterisable** — tunable via `parameter_schema` without code changes.
- **Format-agnostic** — the same preset drives GIF, WebP, WebM, and MOV exporters.
- **Composable** — multiple presets can be applied in sequence in future renderers.

---

## MotionPreset Schema

```python
@dataclass
class MotionPreset:
    id: str                          # Unique identifier
    name: str                        # Human-readable display name
    loopable: bool                   # Does the animation loop seamlessly?
    duration_ms: int                 # Approximate duration in milliseconds
    alpha_safe: bool                 # Preserves transparency?
    overlay_safe: bool               # Suitable for overlay compositing?
    sticker_safe: bool               # Meets Telegram sticker constraints?
    recommended_categories: list     # Asset categories it works best with
    parameter_schema: dict           # Tunable parameter definitions
    description: str                 # Human-readable effect description
```

---

## Built-in Preset Catalog

### `pulse` — Pulse

> Smooth scale-up / scale-down loop that makes the asset breathe.

| Property | Value |
|---|---|
| Loop | ✓ |
| Duration | 800 ms |
| Alpha-safe | ✓ |
| Overlay-safe | ✓ |
| Sticker-safe | ✓ |
| Best for | letter, number, emoji, icon, sticker |

**Parameters:**

| Name | Type | Default | Range |
|---|---|---|---|
| `scale_min` | number | 0.9 | 0.5–1.0 |
| `scale_max` | number | 1.1 | 1.0–2.0 |
| `easing` | string | `ease_in_out` | — |

---

### `glow` — Glow

> Animated outer glow that pulses between low and high intensity.

| Property | Value |
|---|---|
| Loop | ✓ |
| Duration | 1200 ms |
| Alpha-safe | ✓ |
| Overlay-safe | ✓ |
| Sticker-safe | ✓ |
| Best for | letter, number, symbol, signal, icon |

**Parameters:**

| Name | Type | Default |
|---|---|---|
| `glow_color` | string (hex) | `#ffffff` |
| `glow_radius` | number (px) | 12 |
| `intensity_min` | number 0–1 | 0.3 |
| `intensity_max` | number 0–1 | 1.0 |

---

### `wobble` — Wobble

> Left-right rotation oscillation. Best with small icons and emoji.

| Loop | Duration | Overlay-safe |
|---|---|---|
| ✓ | 600 ms | ✗ |

**Parameters:** `angle_deg` (default 8°), `pivot` (default `center`).

---

### `bounce` — Bounce

> Vertical bounce with optional squash-and-stretch on landing.

| Loop | Duration | Overlay-safe |
|---|---|---|
| ✓ | 700 ms | ✗ |

**Parameters:** `amplitude_px` (default 20 px), `squash` (default `true`).

---

### `orbit` — Orbit

> Circular orbit around the asset's centre.

| Loop | Duration | Overlay-safe |
|---|---|---|
| ✓ | 2000 ms | ✓ |

**Parameters:** `radius_px`, `speed_factor`, `clockwise`.

Best for: particle, symbol, icon, frame.

---

### `glitch` — Glitch

> RGB channel shift glitch effect.

| Loop | Duration | Overlay-safe |
|---|---|---|
| ✓ | 500 ms | ✓ |

**Parameters:** `shift_px`, `color_channels`, `frames`.

Best for: letter, number, signal, icon.

---

### `sparkle` — Sparkle

> Twinkling star/sparkle particles orbiting the asset.

| Loop | Duration | Overlay-safe |
|---|---|---|
| ✓ | 1500 ms | ✓ |

**Parameters:** `count`, `size_min_px`, `size_max_px`, `color`.

---

### `particle_burst` — Particle Burst

> One-shot radial particle explosion.

| Loop | Duration | Sticker-safe |
|---|---|---|
| ✗ | 1000 ms | ✗ |

Not sticker-safe because Telegram requires looping animations.

**Parameters:** `particle_count`, `burst_radius_px`, `fade_out`, `color`.

---

### `laser_sweep` — Laser Sweep

> A bright laser line sweeps across the asset.

| Loop | Duration | Overlay-safe |
|---|---|---|
| ✓ | 1000 ms | ✓ |

**Parameters:** `color`, `width_px`, `direction` (`horizontal`/`vertical`/`diagonal`).

---

### `signal_flash` — Signal Flash

> Hard on/off strobe flash effect.

| Loop | Duration | Overlay-safe |
|---|---|---|
| ✓ | 400 ms | ✓ |

**Parameters:** `on_duration_ms`, `off_duration_ms`, `flash_color`.

---

## Adding a New Preset

1. Open `pipeline/motion_presets/catalog.py`.
2. Instantiate a `MotionPreset` with the required fields.
3. Add it to the `PRESETS` dict.
4. Implement the visual effect in each relevant exporter:
   - `pipeline/exporters/gif_exporter.py` → `_render_frames`
   - `pipeline/exporters/webp_exporter.py` → `_render_frames`
   - `pipeline/exporters/webm_exporter.py` → `_render`
5. Update this document.

---

## Preset Compatibility Matrix

| Preset | letter | number | emoji | symbol | signal | frame | particle | icon |
|---|---|---|---|---|---|---|---|---|
| pulse | ✓ | ✓ | ✓ | | | | | ✓ |
| glow | ✓ | ✓ | | ✓ | ✓ | | | ✓ |
| wobble | ✓ | ✓ | ✓ | | | | | ✓ |
| bounce | ✓ | ✓ | ✓ | ✓ | | | | |
| orbit | | | | ✓ | | ✓ | ✓ | ✓ |
| glitch | ✓ | ✓ | | | ✓ | | | ✓ |
| sparkle | | | ✓ | ✓ | | | ✓ | ✓ |
| particle_burst | | | ✓ | ✓ | | | ✓ | ✓ |
| laser_sweep | ✓ | ✓ | | | ✓ | ✓ | | |
| signal_flash | ✓ | | | ✓ | ✓ | | | ✓ |

> Empty cells indicate the preset is not in the preset's `recommended_categories`
> list.  It will still work if applied — these are recommendations, not restrictions.

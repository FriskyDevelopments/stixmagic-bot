# Motion Preset System

Motion presets are the animation vocabulary of the MagicStix pipeline.
Each preset describes *what kind of animation* should be applied to a base
asset.  Presets are intentionally abstract — they do not contain rendering
code.  Actual rendering is the responsibility of the exporters layer.

---

## MotionPreset Schema

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Unique slug (used in output filenames) |
| `name` | `string` | Human-readable label |
| `loopable` | `boolean` | Animation loops seamlessly |
| `duration` | `float` | Total duration in seconds |
| `alpha_safe` | `boolean` | Effect preserves source alpha channel |
| `overlay_safe` | `boolean` | Suitable for transparent overlay use |
| `sticker_safe` | `boolean` | Meets Telegram sticker constraints |
| `recommended_categories` | `string[]` | Best-fit asset categories (empty = all) |
| `parameter_schema` | `object` | Tweakable parameter descriptions |
| `notes` | `string` | Free-form remarks |

---

## Built-in Presets

| ID | Name | Loop | Duration | Alpha | Overlay | Sticker |
|---|---|---|---|---|---|---|
| `pulse` | Pulse | ✅ | 1.5 s | ✅ | ✅ | ✅ |
| `glow` | Glow | ✅ | 2.0 s | ✅ | ✅ | ✅ |
| `wobble` | Wobble | ✅ | 1.0 s | ✅ | ✅ | ✅ |
| `bounce` | Bounce | ✅ | 1.2 s | ✅ | ✅ | ✅ |
| `orbit` | Orbit | ✅ | 3.0 s | ✅ | ✅ | ❌ |
| `glitch` | Glitch | ✅ | 2.0 s | ❌ | ✅ | ✅ |
| `sparkle` | Sparkle | ✅ | 2.5 s | ✅ | ✅ | ✅ |
| `particle_burst` | Particle Burst | ❌ | 1.5 s | ✅ | ✅ | ❌ |
| `laser_sweep` | Laser Sweep | ✅ | 2.0 s | ✅ | ✅ | ✅ |
| `signal_flash` | Signal Flash | ✅ | 0.8 s | ✅ | ✅ | ✅ |

---

## Querying Presets

```python
from pipeline.motion_presets import list_presets, get_preset

# All sticker-safe presets
sticker_presets = list_presets(sticker_safe=True)

# Presets recommended for letters
letter_presets  = list_presets(category="letter")

# Get one by ID
pulse = get_preset("pulse")
print(pulse.duration)   # 1.5
```

---

## Adding a Custom Preset

Add a `MotionPreset` instance to `BUILTIN_PRESETS` in
`pipeline/motion_presets/__init__.py`:

```python
MotionPreset(
    id="my_preset",
    name="My Custom Preset",
    loopable=True,
    duration=2.0,
    alpha_safe=True,
    overlay_safe=True,
    sticker_safe=True,
    recommended_categories=["letter", "symbol"],
    parameter_schema={
        "intensity": {"type": "float", "default": 0.8, "min": 0.0, "max": 1.0},
    },
    notes="Describe what the animation does.",
),
```

The preset will immediately be discoverable via `get_preset()` and `list_presets()`.

---

## Parameter Schema Convention

Each entry in `parameter_schema` is a dict with at minimum:

```json
{
  "type": "float | integer | string | boolean | array",
  "default": <value>
}
```

Numeric types should include `"min"` and `"max"` bounds.
String types with a fixed set of values should include `"options": [...]`.

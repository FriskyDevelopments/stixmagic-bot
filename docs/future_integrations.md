# MagicStix — Future Integrations

This document describes three planned integrations that extend MagicStix beyond
the Telegram bot.  None of these are implemented yet — scaffolding lives under
`integrations/`.

---

## 1. Browser / Nebulosa Extension

**Directory:** `integrations/extension/`  
**Status:** Scaffolding only

### Purpose

A browser extension that triggers MagicStix visual effects in response to
browser and chat events.  The extension is code-named *Nebulosa*.

### Planned Trigger Events

| Event | Example |
|---|---|
| New chat message | Flash / pulse overlay |
| Hand raise | Sparkle burst |
| DJ cue | Laser sweep |
| Moderation signal | Signal flash |
| Custom hotkey | Any preset on demand |

### Architecture

```
Browser Extension (JS)
    │
    │  WebSocket / REST
    ▼
Flask API  (/ws/extension or /api/extension/trigger)
    │
    │  ExtensionEvent object
    ▼
MagicStix Overlay Engine
    │
    │  rendered frames
    ▼
Virtual Camera / OBS Source
```

### Required API Endpoints (not yet implemented)

- `GET /api/assets` — list available assets
- `GET /api/presets` — list available presets
- `POST /api/extension/trigger` — trigger a (asset, preset) render

### Implementation Steps

1. Define `ExtensionEvent` dataclass in `integrations/extension/__init__.py`.
2. Add `/ws/extension` WebSocket endpoint to `api.py`.
3. Implement event-to-preset mapping logic.
4. Build the browser extension manifest + content script.
5. Write end-to-end test.

---

## 2. Overlay / Compositor Engine

**Directory:** `integrations/overlay_engine/`  
**Status:** Scaffolding only

### Purpose

A lightweight OBS-style compositor that uses MagicStix assets as compositable
layers, similar to a simplified After Effects timeline for stream overlays.

### Core Concepts

- **`OverlayScene`** — a named canvas (e.g. 1920×1080) with a list of layers.
- **`OverlayLayer`** — one MagicStix asset positioned on the scene with
  configurable z-index, opacity, and blend mode.
- **`OverlayRenderer`** — combines all layers into a single RGBA frame.

### Architecture

```
OverlayScene
├── OverlayLayer(asset=cloud_symbol, preset=orbit, x=100, y=50, opacity=0.8)
├── OverlayLayer(asset=letter_a_neon, preset=pulse, x=300, y=200)
└── OverlayLayer(asset=wifi_signal, preset=signal_flash, x=800, y=50)
        │
        ▼
OverlayRenderer.render_frame(t=0.5)  →  RGBA numpy array
        │
        ▼
Virtual Camera / OBS NDI Source
```

### Implementation Steps

1. Implement `OverlayScene` + `OverlayLayer` + `OverlayRenderer` in
   `integrations/overlay_engine/__init__.py`.
2. Add a dependency on `numpy` (or `Pillow` compositing).
3. Consume pre-rendered PNG sequences from `renders/png_sequences/` for
   real-time playback.
4. Expose a `/api/overlay/scenes` REST endpoint.
5. Add tests.

---

## 3. Virtual Camera System

**Directory:** `integrations/virtual_camera/`  
**Status:** Scaffolding only

### Purpose

A virtual camera output that feeds the composited MagicStix overlay stream
into virtual camera software, making MagicStix visuals available as a video
input in:

- Zoom
- Google Meet
- Microsoft Teams
- OBS (as an additional source)

### Implementation Options

| Library | Platform | Notes |
|---|---|---|
| `pyvirtualcam` | Linux, macOS, Windows | Easiest Python interface; requires OS-level virtual camera driver |
| NDI SDK | Cross-platform | Professional low-latency video; requires NDI Tools |
| Syphon | macOS | GPU-accelerated frame sharing |
| Spout | Windows | GPU-accelerated frame sharing |

### Architecture

```
Overlay Engine
    │  RGBA frame at N fps
    ▼
VirtualCameraOutput.push_frame(frame)
    │
    │  v4l2loopback (Linux)
    │  OBS Virtual Camera (macOS / Windows)
    ▼
Zoom / Meet / Teams / OBS
```

### Implementation Steps

1. Implement `VirtualCameraOutput` in
   `integrations/virtual_camera/__init__.py`.
2. Wire `OverlayRenderer` → `VirtualCameraOutput` frame loop.
3. Add configuration for frame rate and resolution.
4. Document driver installation for each platform.
5. Add integration test using a headless sink.

---

## Integration Dependency Graph

```
Bot (layer 1)
    └─ generates base assets
        └─ AssetRegistry (layer 2)
            └─ PackGenerator (layer 5)
                └─ Exporters (layer 4)
                    └─ renders/ directory

Browser Extension ─────────────── queries REST API
                                       │
                                   Overlay Engine ── consumes renders/
                                       │
                                   Virtual Camera ── pushes frames
```

---

## Contribution Guide

If you are working on one of these integrations:

1. Create feature branch: `feat/integration/<name>`
2. Implement in the correct `integrations/<name>/` directory.
3. Add a REST endpoint in `api.py` if external access is needed.
4. Write tests under `tests/integrations/`.
5. Update this document.
6. Open a PR referencing this file.

# Future Integrations

This document describes planned integrations that are scaffolded but not yet
implemented.  Each integration consumes assets from the MagicStix pipeline
without depending on the Telegram bot layer.

---

## 1. Browser / Nebulosa Extension

**Module:** `integrations/extension/`  
**Status:** 🚧 Scaffold only

### Purpose

A browser extension (codenamed *Nebulosa*) that triggers MagicStix visual
assets during live events in web applications (Zoom, Google Meet, Twitch chat,
Discord, etc.).

### Trigger Events

| Event | Description |
|---|---|
| `chat_message` | Animate a letter / emoji sticker in response to a message |
| `hand_raise` | Overlay a signal asset when a user raises their hand |
| `dj_cue` | Fire a DJ-pack animation on a DJ event |
| `moderation` | Show a moderation signal on kick / mute / ban events |

### Architecture Plan

```
Browser extension
       │  WebSocket / REST
       ▼
MagicStix asset server  ← serves pre-rendered assets by ID
       │
       ▼
renders/ (gif, webm, webp)  ← files on disk
```

### Implementation Notes

- Assets must be pre-rendered before triggering.
- The extension will query the Flask API (`api.py`) for asset URLs.
- Authentication uses the existing `STIXMAGIC_API_KEY`.

---

## 2. Overlay / Compositor Engine

**Module:** `integrations/overlay_engine/`  
**Status:** 🚧 Scaffold only

### Purpose

A lightweight OBS-style compositor that uses MagicStix assets as named
overlay sources, compositing them over a video feed in real time.

### Planned Capabilities

- Load a pack definition and expose its assets as overlay *sources*
- Composite multiple asset layers at configurable positions and scales
- Apply real-time motion presets to overlay sources
- Output a composited frame stream

### Architecture Plan

```
OverlayCompositor
       │  reads
       ▼
renders/webm/ or renders/mov/  ← pre-rendered overlay assets
       │
       ▼
Composited output (MJPEG stream / WebM pipe / frame buffer)
```

### Implementation Notes

- Static compositing: Pillow (fast, no external dependencies).
- Video compositing: ffmpeg with `-filter_complex overlay`.
- Should be runnable without the Telegram bot.

---

## 3. Virtual Camera System

**Module:** `integrations/virtual_camera/`  
**Status:** 🚧 Scaffold only

### Purpose

Push composited MagicStix visuals to a virtual camera device so they appear
as a camera source in Zoom, Google Meet, OBS, or any WebRTC-based application.

### Platform Support Plan

| Platform | Driver |
|---|---|
| Linux | v4l2loopback + pyfakewebcam |
| macOS | OBS DAL plugin |
| Windows | OBS Virtual Camera |

### Architecture Plan

```
OverlayCompositor
       │  PIL Images / frame buffer
       ▼
VirtualCamera.push_frame()
       │
       ▼
/dev/video0 (or OS virtual camera device)
       │
       ▼
Zoom / Google Meet / OBS input
```

### Implementation Notes

- `VirtualCamera` class accepts a PIL `Image` per frame.
- Target frame rate: 30 fps.
- Resolution presets: 720p (1280×720), 1080p (1920×1080).
- Requires the `pyfakewebcam` library on Linux.

---

## Integration Dependency Map

```
Telegram Bot (main.py)
       │ produces
       ▼
assets/source/           pipeline/
       │                      │
       └──────────────────────┘
                  │
            renders/ + packs/
                  │
       ┌──────────┼────────────┐
       │          │            │
  extension  overlay_engine  virtual_camera
```

The pipeline layer is the only shared dependency between all three integrations.
The bot layer is completely isolated.

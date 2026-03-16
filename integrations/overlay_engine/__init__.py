"""
integrations/overlay_engine – Lightweight compositor integration scaffold.

STATUS: not yet implemented.

Planned functionality
---------------------
This module will provide an OBS-style lightweight compositor that uses
MagicStix assets as compositable layers:

- Load WebM / MOV files with alpha channels from the ``renders/`` directory.
- Stack layers by z-index with configurable opacity and blend modes.
- Apply motion presets in real-time (or pre-render to cache).
- Output a composited RGBA frame stream.

Integration points
------------------
The overlay engine will expose:

1. ``OverlayScene`` – a named collection of layers with a fixed canvas size.
2. ``OverlayLayer`` – one MagicStix asset on a scene with position/opacity.
3. ``OverlayRenderer`` – renders frames on demand or as a live stream.

These will integrate with the virtual camera (``integrations/virtual_camera/``)
to send the composited output to software like Zoom or OBS.

See ``docs/future_integrations.md`` for the full specification.
"""

# Future: define OverlayScene, OverlayLayer, OverlayRenderer here.

"""
integrations/virtual_camera – Virtual camera output integration scaffold.

STATUS: not yet implemented.

Planned functionality
---------------------
This module will provide a virtual camera output that sends the composited
MagicStix overlay stream to virtual camera drivers, making MagicStix visuals
available in:

- Zoom
- Google Meet
- Microsoft Teams
- OBS (as an additional source)

Implementation options
----------------------
1. **pyvirtualcam** (Linux, macOS, Windows) — pure-Python virtual camera sink.
   Requires a compatible virtual camera driver (v4l2loopback on Linux,
   OBS Virtual Camera on macOS/Windows).

2. **NDI SDK** — Network Device Interface for low-latency professional video.

3. **Syphon / Spout** — GPU-accelerated frame sharing on macOS / Windows.

Integration points
------------------
The virtual camera module will:

1. Receive composited RGBA frames from ``integrations/overlay_engine/``.
2. Convert frames to the format required by the chosen sink.
3. Push frames to the virtual camera device at a configurable frame rate.

See ``docs/future_integrations.md`` for the full specification.
"""

# Future: define VirtualCameraOutput and frame-push loop here.

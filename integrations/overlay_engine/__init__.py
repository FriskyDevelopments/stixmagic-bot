"""
integrations/overlay_engine/__init__.py – OBS-style compositor scaffold.

FUTURE INTEGRATION — not yet implemented.

This module will provide the interface between the MagicStix asset pipeline
and a lightweight compositor that layers MagicStix assets over a video feed,
similar to OBS Studio scenes and sources.

Planned capabilities
--------------------
- Load a PackDefinition and expose its assets as overlay *sources*
- Composite multiple asset layers at configurable positions and scales
- Apply real-time motion presets to overlay sources
- Output a composited frame stream (e.g. as MJPEG or piped WebM)

Planned interface
-----------------
>>> from integrations.overlay_engine import OverlayCompositor
>>> compositor = OverlayCompositor()
>>> compositor.load_pack("overlay_starter")
>>> compositor.add_layer("symbol_cloud", preset="sparkle", x=100, y=50)
>>> compositor.start()

Implementation notes
--------------------
- Actual rendering will use Pillow for static layers and ffmpeg for video.
- The compositor should be runnable standalone without the Telegram bot.
- Asset sources will be resolved from the local ``renders/`` directory.
"""

# TODO: implement overlay compositor


class OverlayCompositor:
    """
    Lightweight OBS-style compositor for MagicStix assets.

    NOT YET IMPLEMENTED.
    """

    def load_pack(self, pack_id: str) -> None:
        raise NotImplementedError("OverlayCompositor.load_pack is not yet implemented.")

    def add_layer(self, asset_id: str, preset: str = "pulse", **kwargs) -> None:
        raise NotImplementedError("OverlayCompositor.add_layer is not yet implemented.")

    def start(self) -> None:
        raise NotImplementedError("OverlayCompositor.start is not yet implemented.")

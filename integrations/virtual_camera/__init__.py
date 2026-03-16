"""
integrations/virtual_camera/__init__.py – Virtual camera output scaffold.

FUTURE INTEGRATION — not yet implemented.

This module will provide the interface between the MagicStix compositor and
a virtual camera device (e.g. OBS Virtual Camera, v4l2loopback on Linux,
or the macOS DAL plugin) so MagicStix-composited visuals can appear as a
camera input in Zoom, Google Meet, or any WebRTC-based application.

Planned capabilities
--------------------
- Receive composited frames from the OverlayCompositor
- Push frames to a virtual camera device at a target frame-rate
- Support resolution presets (720p, 1080p)
- Handle start / stop lifecycle cleanly

Planned interface
-----------------
>>> from integrations.virtual_camera import VirtualCamera
>>> cam = VirtualCamera(device="/dev/video0", fps=30, resolution=(1280, 720))
>>> cam.push_frame(composited_pil_image)
>>> cam.start()
>>> cam.stop()

Implementation notes
--------------------
- Linux: uses v4l2loopback and pyfakewebcam.
- macOS: requires the OBS DAL plugin or a third-party virtual camera.
- Windows: requires OBS Virtual Camera or equivalent driver.
- This module should NOT depend on the bot layer.
"""

# TODO: implement virtual camera integration


class VirtualCamera:
    """
    Pushes composited MagicStix frames to a virtual camera device.

    NOT YET IMPLEMENTED.
    """

    def __init__(self, device: str = "/dev/video0", fps: int = 30,
                 resolution: tuple[int, int] = (1280, 720)) -> None:
        self.device = device
        self.fps = fps
        self.resolution = resolution

    def push_frame(self, frame) -> None:
        raise NotImplementedError("VirtualCamera.push_frame is not yet implemented.")

    def start(self) -> None:
        raise NotImplementedError("VirtualCamera.start is not yet implemented.")

    def stop(self) -> None:
        raise NotImplementedError("VirtualCamera.stop is not yet implemented.")

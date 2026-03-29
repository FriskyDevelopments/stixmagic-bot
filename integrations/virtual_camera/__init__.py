"""
integrations/virtual_camera/__init__.py – virtual camera state adapter.

This module tracks a simple virtual-camera lifecycle and accepts frame
objects for consumers that will eventually push frames to OS-specific
virtual camera backends.
"""

from __future__ import annotations


class VirtualCamera:
    """Pushes composited MagicStix frames to a virtual camera device."""

    def __init__(
        self,
        device: str = "/dev/video0",
        fps: int = 30,
        resolution: tuple[int, int] = (1280, 720),
    ) -> None:
        if fps <= 0:
            raise ValueError("fps must be greater than 0")
        if resolution[0] <= 0 or resolution[1] <= 0:
            raise ValueError("resolution values must be greater than 0")

        self.device = device
        self.fps = fps
        self.resolution = resolution
        self._running = False
        self._last_frame = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_frame(self):
        return self._last_frame

    def push_frame(self, frame) -> None:
        if not self._running:
            raise RuntimeError("VirtualCamera.start must be called before push_frame")
        if frame is None:
            raise ValueError("frame cannot be None")
        self._last_frame = frame

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

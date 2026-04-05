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
        """
        Create a VirtualCamera configured for a specific device path, frame rate, and resolution.
        
        Parameters:
            device (str): Path or identifier of the virtual video device (e.g., "/dev/video0").
            fps (int): Target frames per second; must be greater than 0.
            resolution (tuple[int, int]): (width, height) in pixels; both values must be greater than 0.
        
        Raises:
            ValueError: If `fps` is less than or equal to 0 or if either resolution dimension is less than or equal to 0.
        
        Initial state:
            The instance starts stopped (not running) and has no last frame stored.
        """
        # Validate fps is numeric and > 0
        if not isinstance(fps, (int, float)):
            raise ValueError("fps must be a numeric type")
        if fps <= 0:
            raise ValueError("fps must be greater than 0")

        # Validate resolution is a sequence of exactly two numeric items, both > 0
        try:
            if len(resolution) != 2:
                raise ValueError("resolution must contain exactly two values (width, height)")
            width, height = resolution
            if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
                raise ValueError("resolution values must be numeric (int or float)")
            if width <= 0 or height <= 0:
                raise ValueError("resolution values must be greater than 0")
        except TypeError:
            raise ValueError("resolution must be a sequence/iterable of two numeric values")

        self.device = device
        self.fps = fps
        self.resolution = resolution
        self._running = False
        self._last_frame = None

    @property
    def running(self) -> bool:
        """
        Indicates whether the virtual camera is currently started.
        
        Returns:
            True if the camera is running, False otherwise.
        """
        return self._running

    @property
    def last_frame(self):
        """
        Get the most recently pushed video frame.
        
        Returns:
            The last frame object stored by push_frame, or None if no frame has been pushed.
        """
        return self._last_frame

    def push_frame(self, frame) -> None:
        """
        Store the provided frame as the camera's most recent frame for consumption by backends.
        
        Parameters:
            frame: The image/frame object to store. This value is forwarded to backends and must not be None.
        
        Raises:
            RuntimeError: If the virtual camera has not been started.
            ValueError: If `frame` is None.
        """
        if not self._running:
            raise RuntimeError("VirtualCamera.start must be called before push_frame")
        if frame is None:
            raise ValueError("frame cannot be None")
        self._last_frame = frame

    def start(self) -> None:
        """
        Start the virtual camera so it can accept frames.
        
        Sets the camera's running state to True.
        """
        self._running = True

    def stop(self) -> None:
        """
        Stop the virtual camera and mark it as not running.
        
        After calling this method, the `running` property will be `False` and the camera will refuse frames until restarted.
        """
        self._running = False
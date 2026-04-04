"""
integrations/overlay_engine/__init__.py – lightweight overlay compositor.

The compositor keeps a minimal in-memory scene graph for assets in a pack.
It is intentionally renderer-agnostic so bot and pipeline layers can prepare
scenes before handing off to a real-time renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class OverlayLayer:
    """Single overlay layer definition."""

    asset_id: str
    preset: str = "pulse"
    x: int = 0
    y: int = 0
    scale: float = 1.0
    opacity: float = 1.0


class OverlayCompositor:
    """Lightweight OBS-style compositor state container."""

    def __init__(self, renders_root: str = "renders") -> None:
        """
        Initialize the OverlayCompositor and its in-memory state.
        
        Parameters:
            renders_root (str): Filesystem path used as the base directory for compositor renders; stored as a Path.
        """
        self.renders_root = Path(renders_root)
        self.pack_id: str | None = None
        self.layers: list[OverlayLayer] = []
        self.running = False

    def load_pack(self, pack_id: str) -> None:
        """
        Set the active overlay pack for the compositor and clear any existing layers.
        
        Parameters:
            pack_id (str): Identifier of the overlay pack to load; whitespace is trimmed.
        
        Raises:
            ValueError: If `pack_id` is not a non-empty string.
        """
        if not isinstance(pack_id, str) or not pack_id.strip():
            raise ValueError("pack_id must be a non-empty string")
        self.pack_id = pack_id.strip()
        self.layers.clear()

    def add_layer(self, asset_id: str, preset: str = "pulse", **kwargs) -> None:
        """
        Add a new overlay layer to the current pack's scene.
        
        Parameters:
            asset_id (str): Identifier of the asset to add; must be a non-empty string.
            preset (str): Visual preset name; empty values default to "pulse".
            **kwargs: Optional placement and appearance overrides:
                x (int): Horizontal position (converted to int, defaults to 0).
                y (int): Vertical position (converted to int, defaults to 0).
                scale (float): Scale factor (converted to float, defaults to 1.0).
                opacity (float): Opacity (converted to float, defaults to 1.0).
        
        Raises:
            RuntimeError: If no pack has been loaded via `load_pack`.
            ValueError: If `asset_id` is not a non-empty string.
        """
        if self.pack_id is None:
            raise RuntimeError("load_pack must be called before add_layer")
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError("asset_id must be a non-empty string")

        # Normalize preset: None or empty/whitespace -> "pulse"
        if preset is None or (isinstance(preset, str) and not preset.strip()):
            normalized_preset = "pulse"
        else:
            normalized_preset = str(preset).strip()

        layer = OverlayLayer(
            asset_id=asset_id.strip(),
            preset=normalized_preset,
            x=int(kwargs.get("x", 0)),
            y=int(kwargs.get("y", 0)),
            scale=float(kwargs.get("scale", 1.0)),
            opacity=float(kwargs.get("opacity", 1.0)),
        )
        self.layers.append(layer)

    def start(self) -> None:
        """
        Mark the compositor as running after ensuring a pack is loaded.
        
        Raises:
            RuntimeError: If no pack has been loaded via `load_pack` (i.e., `pack_id` is None).
        """
        if self.pack_id is None:
            raise RuntimeError("load_pack must be called before start")
        self.running = True

    def stop(self) -> None:
        """
        Mark the compositor as not running.
        
        Clears the running state so subsequent scene updates or rendering operations are considered stopped.
        """
        self.running = False

    def scene(self) -> dict[str, object]:
        """
        Serialize the compositor's current state into a snapshot dictionary.
        
        Returns:
            snapshot (dict[str, object]): A serializable dictionary with keys:
                - "pack_id": current pack identifier or None
                - "running": `True` if the compositor is started, `False` otherwise
                - "layer_count": number of layers in the scene
                - "layers": list of layer dictionaries (shallow copies of each layer's __dict__)
        """
        return {
            "pack_id": self.pack_id,
            "running": self.running,
            "layer_count": len(self.layers),
            "layers": [layer.__dict__.copy() for layer in self.layers],
        }
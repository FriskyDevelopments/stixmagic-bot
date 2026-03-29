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
        self.renders_root = Path(renders_root)
        self.pack_id: str | None = None
        self.layers: list[OverlayLayer] = []
        self.running = False

    def load_pack(self, pack_id: str) -> None:
        if not isinstance(pack_id, str) or not pack_id.strip():
            raise ValueError("pack_id must be a non-empty string")
        self.pack_id = pack_id.strip()
        self.layers.clear()

    def add_layer(self, asset_id: str, preset: str = "pulse", **kwargs) -> None:
        if self.pack_id is None:
            raise RuntimeError("load_pack must be called before add_layer")
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError("asset_id must be a non-empty string")

        layer = OverlayLayer(
            asset_id=asset_id.strip(),
            preset=str(preset).strip() or "pulse",
            x=int(kwargs.get("x", 0)),
            y=int(kwargs.get("y", 0)),
            scale=float(kwargs.get("scale", 1.0)),
            opacity=float(kwargs.get("opacity", 1.0)),
        )
        self.layers.append(layer)

    def start(self) -> None:
        if self.pack_id is None:
            raise RuntimeError("load_pack must be called before start")
        self.running = True

    def stop(self) -> None:
        self.running = False

    def scene(self) -> dict[str, object]:
        """Return a serializable snapshot of the current compositor state."""
        return {
            "pack_id": self.pack_id,
            "running": self.running,
            "layer_count": len(self.layers),
            "layers": [layer.__dict__.copy() for layer in self.layers],
        }

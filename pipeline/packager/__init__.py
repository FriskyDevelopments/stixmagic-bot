"""pipeline/packager – Metadata-driven product pack generation."""

from .pack import Pack
from .generator import PackGenerator

__all__ = ["Pack", "PackGenerator"]

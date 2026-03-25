from __future__ import annotations

from dataclasses import dataclass
import io


@dataclass(frozen=True)
class CoreMediaRequest:
    """Transport-agnostic media payload used by the shared core engine."""

    file_id: str
    media_type: str
    sticker_format: str


@dataclass(frozen=True)
class CoreMediaResult:
    """Core conversion result consumed by platform adapters."""

    sticker_file: io.BytesIO
    sticker_format: str
    media_type: str

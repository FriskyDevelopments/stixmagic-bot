"""
pipeline/exporters/base.py – Abstract base class for all MagicStix exporters.

Every exporter receives an :class:`~pipeline.asset_model.asset.Asset` and a
:class:`~pipeline.motion_presets.preset.MotionPreset`, then writes one or more
output files to the ``renders/`` directory tree.

Concrete exporters must implement :meth:`BaseExporter.export`.

The pipeline calls exporters through the common interface so that a single
pipeline run can produce every target format by iterating over a list of
registered exporters.
"""

from __future__ import annotations

import abc
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pipeline._paths import RENDERS_DIR
from pipeline.asset_model.asset import Asset
from pipeline.motion_presets.preset import MotionPreset

# Root directory where rendered outputs are written.
_DEFAULT_RENDERS_DIR: Path = RENDERS_DIR


@dataclass
class ExportResult:
    """
    Describes the outcome of a single export operation.

    Attributes:
        format:     Short format label (e.g. ``"gif"``, ``"webm"``).
        path:       Absolute path of the written file (or ``None`` on failure).
        success:    True when the file was written successfully.
        message:    Human-readable status or error message.
        size_bytes: File size in bytes (0 if unknown or failed).
    """

    format: str
    path: Optional[str] = None
    success: bool = False
    message: str = ""
    size_bytes: int = 0


class BaseExporter(abc.ABC):
    """
    Abstract base class for MagicStix format exporters.

    Subclasses implement :meth:`export` to produce one or more output files.

    Attributes:
        format_id:   Short identifier for the output format (e.g. ``"gif"``).
        renders_dir: Root directory for rendered outputs.
    """

    format_id: str = "unknown"

    def __init__(self, renders_dir: Optional[str] = None) -> None:
        self.renders_dir = Path(renders_dir).resolve() if renders_dir else _DEFAULT_RENDERS_DIR

    @abc.abstractmethod
    def export(self, asset: Asset, preset: MotionPreset) -> ExportResult:
        """
        Render *asset* with *preset* and write the result to disk.

        Must return an :class:`ExportResult` describing success or failure.
        """

    # ── Helpers ───────────────────────────────────────────────

    def output_path(self, asset: Asset, preset: MotionPreset, suffix: str = "") -> str:
        """
        Build the canonical output file path for an (asset, preset) pair.

        Convention: ``renders/<format>/<asset_id>_<preset_id><suffix>.<ext>``
        """
        subdir = self.renders_dir / self.format_id
        subdir.mkdir(parents=True, exist_ok=True)
        filename = f"{asset.id}_{preset.id}{suffix}.{self.format_id}"
        return str(subdir / filename)

    def create_result_ok(self, path: str) -> ExportResult:
        size = os.path.getsize(path) if os.path.exists(path) else 0
        return ExportResult(
            format=self.format_id,
            path=path,
            success=True,
            message="OK",
            size_bytes=size,
        )

    def create_result_err(self, message: str) -> ExportResult:
        return ExportResult(
            format=self.format_id,
            success=False,
            message=message,
        )

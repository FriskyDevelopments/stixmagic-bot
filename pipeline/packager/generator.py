import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Type

from pipeline._paths import PACKS_DIR
from pipeline.asset_model.asset import Asset
from pipeline.exporters.base import BaseExporter, ExportResult
from pipeline.exporters.gif_exporter import GifExporter
from pipeline.exporters.mov_exporter import MovExporter
from pipeline.exporters.png_sequence_exporter import PngSequenceExporter
from pipeline.exporters.thumbnail_exporter import ThumbnailExporter
from pipeline.exporters.webm_exporter import WebmExporter
from pipeline.exporters.webp_exporter import AnimatedWebpExporter
from pipeline.metadata.registry import AssetRegistry
from pipeline.motion_presets.catalog import get_preset
from pipeline.motion_presets.preset import MotionPreset
from pipeline.packager.pack import Pack

logger = logging.getLogger(__name__)

# Default packs directory.
_DEFAULT_PACKS_DIR: Path = PACKS_DIR

# Map from export format id → exporter class
_EXPORTERS: Dict[str, Type[BaseExporter]] = {
    "gif": GifExporter,
    "webp": AnimatedWebpExporter,
    "webm": WebmExporter,
    "mov": MovExporter,
    "png_sequences": PngSequenceExporter,
    "thumbnails": ThumbnailExporter,
}


class PackGenerator:
    """
    Generates all export files for a given product pack.

    The generator:
    1. Loads the pack descriptor from ``packs/<pack_id>/pack.json``.
    2. Resolves each asset ID through the :class:`AssetRegistry`.
    3. Resolves each preset ID through the motion preset catalog.
    4. Calls the appropriate exporter for every (asset, preset, format) triple.
    5. Returns a list of :class:`~pipeline.exporters.base.ExportResult` objects.
    """

    def __init__(
        self,
        registry: AssetRegistry,
        packs_dir: Optional[str] = None,
    ) -> None:
        self._registry = registry
        self._packs_dir = Path(packs_dir).resolve() if packs_dir else _DEFAULT_PACKS_DIR

    # ── Pack loading ──────────────────────────────────────────

    def load_pack(self, pack_id: str) -> Optional[Pack]:
        """
        Load and return the :class:`Pack` for *pack_id*.

        Returns ``None`` if the descriptor file is missing or invalid.
        """
        path = self._packs_dir / pack_id / "pack.json"
        if not path.exists():
            logger.error("Pack descriptor not found: %s", path)
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return Pack.from_dict(data)
        except Exception as exc:
            logger.error("Failed to load pack %s: %s", pack_id, exc)
            return None

    def list_packs(self) -> List[str]:
        """Return IDs of all packs that have a ``pack.json`` descriptor."""
        if not self._packs_dir.is_dir():
            return []
        return [
            p.name
            for p in self._packs_dir.iterdir()
            if p.is_dir() and (p / "pack.json").is_file()
        ]

    # ── Generation ────────────────────────────────────────────

    def _export_format(
        self, pack: Pack, asset: Asset, preset: MotionPreset, fmt: str
    ) -> ExportResult:
        exporter_cls = _EXPORTERS.get(fmt)
        if exporter_cls is None:
            logger.warning(
                "Pack %s: unknown export format %r — skipping", pack.pack_id, fmt
            )
            return ExportResult(
                format=fmt,
                success=False,
                message=f"No exporter for format {fmt!r}",
            )

        exporter = exporter_cls()
        result = exporter.export(asset, preset)

        if result.success:
            logger.info(
                "Pack %s: exported %s+%s → %s (%d bytes)",
                pack.pack_id,
                asset.id,
                preset.id,
                result.path,
                result.size_bytes,
            )
        else:
            logger.error(
                "Pack %s: export FAILED %s+%s fmt=%s: %s",
                pack.pack_id,
                asset.id,
                preset.id,
                fmt,
                result.message,
            )
        return result

    def _process_preset_for_asset(
        self, pack: Pack, asset: Asset, preset_id: str
    ) -> List[ExportResult]:
        try:
            preset = get_preset(preset_id)
        except KeyError as exc:
            logger.warning("Pack %s: %s — skipping", pack.pack_id, exc)
            return [ExportResult(format="unknown", success=False, message=str(exc))]

        if not asset.is_animation_compatible(preset_id):
            logger.info(
                "Pack %s: asset %s is not compatible with preset %s — skipping",
                pack.pack_id,
                asset.id,
                preset_id,
            )
            return []

        results = []
        for fmt in pack.export_formats:
            results.append(self._export_format(pack, asset, preset, fmt))
        return results

    def _process_asset(self, pack: Pack, asset_id: str) -> List[ExportResult]:
        asset = self._registry.get(asset_id)
        if asset is None:
            logger.warning(
                "Pack %s: asset %s not found in registry — skipping",
                pack.pack_id,
                asset_id,
            )
            return [
                ExportResult(
                    format="unknown",
                    success=False,
                    message=f"Asset {asset_id!r} not in registry",
                )
            ]

        results = []
        for preset_id in pack.included_motion_presets:
            results.extend(self._process_preset_for_asset(pack, asset, preset_id))
        return results

    def generate(self, pack_id: str) -> List[ExportResult]:
        """
        Generate all export files for *pack_id*.

        Returns a flat list of :class:`ExportResult` objects — one per
        (asset, preset, format) triple attempted.
        """
        pack = self.load_pack(pack_id)
        if pack is None:
            return [
                ExportResult(
                    format="unknown",
                    success=False,
                    message=f"Pack {pack_id!r} not found",
                )
            ]

        results: List[ExportResult] = []

        for asset_id in pack.included_assets:
            results.extend(self._process_asset(pack, asset_id))

        return results

    def generate_all(self) -> Dict[str, List[ExportResult]]:
        """Generate outputs for every registered pack. Returns a dict keyed by pack_id."""
        return {pack_id: self.generate(pack_id) for pack_id in self.list_packs()}

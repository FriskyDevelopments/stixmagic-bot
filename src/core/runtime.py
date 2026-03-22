from __future__ import annotations

from dataclasses import dataclass, field

from src.config.settings import RuntimeSettings, load_runtime_settings
from src.core.plugins import PluginRegistry
from src.plugins.truck_club.plugin import TruckClubPlugin
from src.types.plugin import PluginManifest


@dataclass(slots=True, frozen=True)
class RuntimeBoundary:
    owner: str
    responsibilities: tuple[str, ...]


@dataclass(slots=True)
class ApplicationRuntime:
    settings: RuntimeSettings
    core_boundaries: tuple[RuntimeBoundary, ...]
    plugin_registry: PluginRegistry = field(default_factory=PluginRegistry)

    def enabled_plugin_manifests(self) -> list[PluginManifest]:
        enabled = set(self.settings.bot.enabled_plugins)
        manifests = []
        for manifest in self.plugin_registry.manifests():
            if not enabled or manifest.slug in enabled:
                manifests.append(manifest)
        return manifests


def build_runtime() -> ApplicationRuntime:
    settings = load_runtime_settings()
    runtime = ApplicationRuntime(
        settings=settings,
        core_boundaries=(
            RuntimeBoundary(
                owner="src/bot",
                responsibilities=(
                    "telegram runtime orchestration",
                    "conversation flow control",
                    "shared event handling",
                ),
            ),
            RuntimeBoundary(
                owner="src/stickers",
                responsibilities=(
                    "sticker conversion",
                    "mask-based cutout processing",
                    "media ingestion helpers",
                ),
            ),
            RuntimeBoundary(
                owner="src/animations",
                responsibilities=(
                    "animation preset access",
                    "sphere and motion pipeline coordination",
                    "asset export adapters",
                ),
            ),
        ),
    )
    runtime.plugin_registry.register(TruckClubPlugin(settings.truck_club))
    return runtime

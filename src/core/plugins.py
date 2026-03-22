from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from src.types.plugin import PluginManifest


class BotPlugin(Protocol):
    """Minimal runtime boundary for optional plugin packages."""

    def manifest(self) -> PluginManifest: ...


@dataclass(slots=True)
class PluginRegistry:
    """Keeps plugin-owned functionality out of the core bot namespace."""

    _plugins: dict[str, BotPlugin] = field(default_factory=dict)

    def register(self, plugin: BotPlugin) -> None:
        manifest = plugin.manifest()
        self._plugins[manifest.slug] = plugin

    def get(self, slug: str) -> BotPlugin | None:
        return self._plugins.get(slug)

    def manifests(self) -> list[PluginManifest]:
        return [plugin.manifest() for plugin in self._plugins.values()]

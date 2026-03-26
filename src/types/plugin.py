from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(slots=True, frozen=True)
class PluginCommand:
    """Declarative command owned by a plugin, not the core bot."""

    name: str
    description: str
    handler_name: str


@dataclass(slots=True, frozen=True)
class PluginHook:
    """Named integration hook exposed by the core bot runtime."""

    event: str
    callback_name: str


@dataclass(slots=True, frozen=True)
class PluginMetric:
    """Plugin-owned metric or telemetry signal."""

    name: str
    description: str


@dataclass(slots=True, frozen=True)
class PluginManifest:
    """Summary of a plugin's ownership boundary."""

    slug: str
    display_name: str
    config_namespace: str
    commands: tuple[PluginCommand, ...] = field(default_factory=tuple)
    hooks: tuple[PluginHook, ...] = field(default_factory=tuple)
    metrics: tuple[PluginMetric, ...] = field(default_factory=tuple)
    description: str = ""

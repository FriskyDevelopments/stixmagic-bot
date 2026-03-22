from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import TruckClubSettings
from src.types.plugin import PluginCommand, PluginHook, PluginManifest, PluginMetric


@dataclass(slots=True, frozen=True)
class TruckClubPlugin:
    """Truck Club integration surface, isolated from general bot concerns."""

    settings: TruckClubSettings

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            slug="truck-club",
            display_name="The Truck Club",
            config_namespace="TRUCK_CLUB_*",
            description=(
                "Owns Truck Club-specific commands, event hooks, and metrics without "
                "bleeding those rules into the shared sticker bot runtime."
            ),
            commands=(
                PluginCommand(
                    name="/truckclub",
                    description="Entry point for Truck Club-specific workflows.",
                    handler_name="truck_club_command",
                ),
            ),
            hooks=(
                PluginHook(
                    event="pack_created",
                    callback_name="record_truck_club_pack_creation",
                ),
            ),
            metrics=(
                PluginMetric(
                    name=f"{self.settings.metrics_prefix}.pack_created",
                    description="Counts packs created through Truck Club flows.",
                ),
                PluginMetric(
                    name=f"{self.settings.metrics_prefix}.command_invoked",
                    description="Counts Truck Club command invocations.",
                ),
            ),
        )

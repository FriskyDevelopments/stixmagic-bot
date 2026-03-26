from __future__ import annotations

import os
from dataclasses import dataclass, field


def _csv_env(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, "")
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(items)


@dataclass(slots=True, frozen=True)
class BotSettings:
    telegram_bot_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    api_key: str = field(default_factory=lambda: os.environ.get("STIXMAGIC_API_KEY", ""))
    miniapp_url: str = field(default_factory=lambda: os.environ.get("MINIAPP_URL", ""))
    enabled_plugins: tuple[str, ...] = field(default_factory=lambda: _csv_env("STIXMAGIC_ENABLED_PLUGINS"))


@dataclass(slots=True, frozen=True)
class TruckClubSettings:
    enabled: bool = field(default_factory=lambda: os.environ.get("TRUCK_CLUB_ENABLED", "0") == "1")
    guild_id: str = field(default_factory=lambda: os.environ.get("TRUCK_CLUB_GUILD_ID", ""))
    metrics_prefix: str = field(default_factory=lambda: os.environ.get("TRUCK_CLUB_METRICS_PREFIX", "truck_club"))


@dataclass(slots=True, frozen=True)
class RuntimeSettings:
    bot: BotSettings = field(default_factory=BotSettings)
    truck_club: TruckClubSettings = field(default_factory=TruckClubSettings)


def load_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings()

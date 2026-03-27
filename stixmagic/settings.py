"""Centralized environment and deployment settings."""

from __future__ import annotations

import logging
import os
import warnings
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


def _clean_url(value: str) -> str:
    return value.rstrip("/")


@dataclass(frozen=True)
class AppSettings:
    telegram_bot_token: str
    telegram_bot_username: str
    stixmagic_api_key: str
    database_path: str
    public_base_url: str
    api_base_url: str
    miniapp_path: str
    bot_mode: str
    webhook_url: str
    webhook_secret: str

    @property
    def miniapp_url(self) -> str:
        return f"{self.public_base_url}{self.miniapp_path}" if self.public_base_url else ""

    @property
    def miniapp_api_base_url(self) -> str:
        return f"{self.api_base_url}/miniapp" if self.api_base_url else ""


def _infer_public_base_url() -> str:
    explicit = os.environ.get("STIXMAGIC_PUBLIC_BASE_URL", "").strip()
    if explicit:
        return _clean_url(explicit)

    domains = os.environ.get("REPLIT_DOMAINS", "").strip()
    if domains:
        first = domains.split(",")[0].strip()
        if first:
            return f"https://{first}"

    return ""


def _infer_bot_username() -> str:
    """
    Infer the bot username from TELEGRAM_BOT_USERNAME.
    Raises an exception if not set to prevent incorrect deep link generation.
    """
    explicit = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip()
    if explicit:
        return explicit.lstrip("@")

    # Fail closed: do not fall back to a hardcoded username
    # Deployments MUST set TELEGRAM_BOT_USERNAME to generate correct deep links
    raise ValueError(
        "TELEGRAM_BOT_USERNAME environment variable is not set. "
        "Set it to your bot's username (without @) to enable deep link generation."
    )


# Module-level cache for AppSettings instance
_CACHED_SETTINGS: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """
    Get the application settings singleton.
    Uses a cached instance to avoid repeated environment parsing.
    """
    global _CACHED_SETTINGS

    if _CACHED_SETTINGS is not None:
        return _CACHED_SETTINGS

    public_base_url = _infer_public_base_url()
    api_base_url = f"{public_base_url}/api" if public_base_url else "/api"

    # Allow bot_username to be empty but raise if deep links are attempted
    # This enables read-only API operations when the bot is not configured
    try:
        bot_username = _infer_bot_username()
    except ValueError as e:
        # Allow settings to load with empty bot_username
        # Deep link generation will fail gracefully at runtime
        bot_username = ""
        # Emit a startup warning so operators know about the misconfiguration
        warning_msg = (
            "TELEGRAM_BOT_USERNAME environment variable is not set. "
            "Deep link generation will fail at runtime. "
            "Set TELEGRAM_BOT_USERNAME to your bot's username (without @) to enable deep links."
        )
        logger.warning(warning_msg)
        warnings.warn(warning_msg, UserWarning, stacklevel=2)

    _CACHED_SETTINGS = AppSettings(
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_bot_username=bot_username,
        stixmagic_api_key=os.environ.get("STIXMAGIC_API_KEY", "").strip(),
        database_path=os.environ.get("STIXMAGIC_DB_PATH", "bot.db").strip() or "bot.db",
        public_base_url=public_base_url,
        api_base_url=api_base_url,
        miniapp_path=os.environ.get("STIXMAGIC_MINIAPP_PATH", "/miniapp").strip() or "/miniapp",
        bot_mode=os.environ.get("TELEGRAM_BOT_MODE", "polling").strip().lower() or "polling",
        webhook_url=os.environ.get("TELEGRAM_WEBHOOK_URL", "").strip(),
        webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip(),
    )

    return _CACHED_SETTINGS


def clear_cached_settings() -> None:
    """
    Clear the cached settings instance.
    Useful for tests or when environment variables change at runtime.
    """
    global _CACHED_SETTINGS
    _CACHED_SETTINGS = None
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_dotenv_loaded = False


def _ensure_dotenv() -> None:
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv()
        _dotenv_loaded = True


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
        if not self.public_base_url:
            return ""
        return f"{self.public_base_url}{self.miniapp_path}"

    @property
    def miniapp_api_base_url(self) -> str:
        if not self.api_base_url:
            return ""
        return f"{self.api_base_url}/miniapp"



def _strip_at_sign(value: str) -> str:
    return value[1:] if value.startswith("@") else value



def _infer_public_base_url() -> str:
    explicit = os.environ.get("STIXMAGIC_PUBLIC_BASE_URL", "").strip().rstrip("/")
    return explicit


def _env_suffix() -> str:
    mode = os.environ.get("APP_ENV", "development").strip().lower()
    return {"production": "PROD", "test": "TEST"}.get(mode, "DEV")


def _resolve_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def get_settings() -> AppSettings:
    _ensure_dotenv()

    suffix = _env_suffix()
    public_base_url = _infer_public_base_url()
    miniapp_path = os.environ.get("STIXMAGIC_MINIAPP_PATH", "/miniapp").strip() or "/miniapp"
    if not miniapp_path.startswith("/"):
        miniapp_path = f"/{miniapp_path}"

    api_base_url = f"{public_base_url}/api" if public_base_url else "/api"

    telegram_bot_token = _resolve_env("TELEGRAM_BOT_TOKEN", f"BOT_TOKEN_{suffix}")
    if not telegram_bot_token:
        raise ValueError(
            f"Missing required telegram_bot_token. Set either TELEGRAM_BOT_TOKEN or BOT_TOKEN_{suffix} "
            f"environment variable. Current APP_ENV suffix: {suffix}"
        )

    return AppSettings(
        telegram_bot_token=telegram_bot_token,
        telegram_bot_username=_strip_at_sign(os.environ.get("TELEGRAM_BOT_USERNAME", "").strip()),
        stixmagic_api_key=_resolve_env("STIXMAGIC_API_KEY", f"STIXMAGIC_API_KEY_{suffix}"),
        database_path=os.environ.get("STIXMAGIC_DB_PATH", "").strip() or "bot.db",
        public_base_url=public_base_url,
        api_base_url=api_base_url,
        miniapp_path=miniapp_path,
        bot_mode=(os.environ.get("TELEGRAM_BOT_MODE", "polling").strip() or "polling").lower(),
        webhook_url=os.environ.get("TELEGRAM_WEBHOOK_URL", "").strip(),
        webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip(),
    )
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


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
    if explicit:
        return explicit

    domains = os.environ.get("REPLIT_DOMAINS", "").strip()
    if not domains:
        return ""

    primary = domains.split(",")[0].strip()
    if not primary:
        return ""
    return f"https://{primary}"


def get_settings() -> AppSettings:
    public_base_url = _infer_public_base_url()
    miniapp_path = os.environ.get("STIXMAGIC_MINIAPP_PATH", "/miniapp").strip() or "/miniapp"
    if not miniapp_path.startswith("/"):
        miniapp_path = f"/{miniapp_path}"

    api_base_url = f"{public_base_url}/api" if public_base_url else "/api"

    return AppSettings(
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_bot_username=_strip_at_sign(os.environ.get("TELEGRAM_BOT_USERNAME", "").strip()),
        stixmagic_api_key=os.environ.get("STIXMAGIC_API_KEY", "").strip(),
        database_path=os.environ.get("STIXMAGIC_DB_PATH", "").strip() or "bot.db",
        public_base_url=public_base_url,
        api_base_url=api_base_url,
        miniapp_path=miniapp_path,
        bot_mode=(os.environ.get("TELEGRAM_BOT_MODE", "polling").strip() or "polling").lower(),
        webhook_url=os.environ.get("TELEGRAM_WEBHOOK_URL", "").strip(),
        webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip(),
    )

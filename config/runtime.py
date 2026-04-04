from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

VALID_ENVS = {"development", "production", "test"}
TOKEN_PATTERN = re.compile(r"\d+:[A-Za-z0-9_-]+")


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    app_env: str
    telegram_bot_token: str
    api_key: str
    session_secret: str
    miniapp_url: str
    port: int

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"



def _normalize_env(value: str | None) -> str:
    normalized = (value or "development").strip().lower()
    if normalized not in VALID_ENVS:
        valid = ", ".join(sorted(VALID_ENVS))
        raise ConfigError(f"APP_ENV must be one of: {valid}. Got: {value!r}")
    return normalized



def _env_suffix(app_env: str) -> str:
    return {"development": "DEV", "production": "PROD", "test": "TEST"}[app_env]


def _env_candidates(base_name: str, app_env: str) -> list[str]:
    suffix = _env_suffix(app_env)
    return [f"{base_name}_{suffix}", base_name]



def _resolve_optional(base_name: str, app_env: str, default: str = "") -> str:
    for candidate in _env_candidates(base_name, app_env):
        value = os.environ.get(candidate)
        if value:
            return value.strip()
    return default



def _resolve_required(base_name: str, app_env: str, *, aliases: tuple[str, ...] = ()) -> str:
    for alias in aliases:
        value = os.environ.get(alias)
        if value:
            return value.strip()

    for candidate in _env_candidates(base_name, app_env):
        value = os.environ.get(candidate)
        if value:
            return value.strip()

    searched = ", ".join([*_env_candidates(base_name, app_env), *aliases])
    raise ConfigError(
        f"Missing required environment variable for {base_name}. Expected one of: {searched}."
    )



def _validate_token(raw_token: str) -> str:
    match = TOKEN_PATTERN.search(raw_token)
    if not match:
        raise ConfigError(
            "Telegram bot token is invalid. Set BOT_TOKEN_DEV/BOT_TOKEN_PROD or TELEGRAM_BOT_TOKEN to a valid BotFather token."
        )
    return match.group(0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = _normalize_env(os.environ.get("APP_ENV"))
    token = _validate_token(
        _resolve_required("BOT_TOKEN", app_env, aliases=("TELEGRAM_BOT_TOKEN",))
    )
    api_key = _resolve_required("STIXMAGIC_API_KEY", app_env)
    session_secret = _resolve_optional("SESSION_SECRET", app_env)
    if not session_secret and app_env == "production":
        raise ConfigError(
            "SESSION_SECRET_PROD (or SESSION_SECRET) is required when APP_ENV=production."
        )
    miniapp_url = _resolve_optional("MINIAPP_URL", app_env)
    port = int(os.environ.get("PORT", "5000"))
    return Settings(
        app_env=app_env,
        telegram_bot_token=token,
        api_key=api_key,
        session_secret=session_secret,
        miniapp_url=miniapp_url,
        port=port,
    )



def describe_expected_variables(app_env: str | None = None) -> list[str]:
    resolved_env = _normalize_env(app_env or os.environ.get("APP_ENV"))
    return [
        f"BOT_TOKEN_{_env_suffix(resolved_env)} (or TELEGRAM_BOT_TOKEN)",
        f"STIXMAGIC_API_KEY_{_env_suffix(resolved_env)} (or STIXMAGIC_API_KEY)",
        f"SESSION_SECRET_{_env_suffix(resolved_env)} (or SESSION_SECRET for production)",
        f"MINIAPP_URL_{_env_suffix(resolved_env)} (or MINIAPP_URL)",
    ]

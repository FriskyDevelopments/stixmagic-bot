from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

VALID_ENVS = {"development", "production"}
TOKEN_PATTERN = re.compile(r"\d+:[A-Za-z0-9_-]+")


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    app_env: str
    telegram_bot_token: str
    telegram_token_source: str
    api_key: str
    api_key_source: str
    session_secret: str
    session_secret_source: str | None
    miniapp_url: str
    miniapp_url_source: str | None
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


def _normalize_value(value: str | None) -> str:
    return (value or "").strip()


def _resolve_single(name: str) -> str:
    return _normalize_value(os.environ.get(name))


def _resolve_exactly_one(*, config_name: str, required: bool, candidates: tuple[str, ...]) -> tuple[str, str | None]:
    provided: list[tuple[str, str]] = []
    for candidate in candidates:
        value = _resolve_single(candidate)
        if value:
            provided.append((candidate, value))

    if not provided:
        if required:
            raise ConfigError(
                f"Missing required setting {config_name}. Set exactly one of: {', '.join(candidates)}."
            )
        return "", None

    unique_values = {value for _, value in provided}
    if len(unique_values) > 1:
        var_names = ", ".join(name for name, _ in provided)
        raise ConfigError(
            f"Ambiguous setting {config_name}. Multiple variables are set with different values: {var_names}."
        )

    if len(provided) > 1:
        var_names = ", ".join(name for name, _ in provided)
        raise ConfigError(
            f"Ambiguous setting {config_name}. Set only one variable, but found: {var_names}."
        )

    return provided[0][1], provided[0][0]


def _validate_token(raw_token: str, token_source: str | None) -> str:
    match = TOKEN_PATTERN.search(raw_token)
    if not match:
        source_label = token_source or "<unknown>"
        raise ConfigError(
            f"Telegram bot token from {source_label} is invalid. Use a valid BotFather token format like 123456:ABCDEF..."
        )
    return match.group(0)


def _resolve_token(app_env: str) -> tuple[str, str]:
    if app_env == "development":
        token, source = _resolve_exactly_one(
            config_name="telegram_bot_token",
            required=True,
            candidates=("DEV_BOT_TOKEN", "TELEGRAM_BOT_TOKEN_DEV", "BOT_TOKEN_DEV"),
        )
        if _resolve_single("TELEGRAM_BOT_TOKEN") or _resolve_single("BOT_TOKEN"):
            raise ConfigError(
                "APP_ENV=development forbids production token variables TELEGRAM_BOT_TOKEN/BOT_TOKEN. "
                "Use DEV_BOT_TOKEN or TELEGRAM_BOT_TOKEN_DEV only."
            )
        return _validate_token(token, source), source or ""

    token, source = _resolve_exactly_one(
        config_name="telegram_bot_token",
        required=True,
        candidates=("TELEGRAM_BOT_TOKEN", "BOT_TOKEN"),
    )
    return _validate_token(token, source), source or ""


def _resolve_api_key(app_env: str) -> tuple[str, str]:
    if app_env == "development":
        return _resolve_exactly_one(
            config_name="api_key",
            required=True,
            candidates=("STIXMAGIC_API_KEY_DEV",),
        )
    return _resolve_exactly_one(
        config_name="api_key",
        required=True,
        candidates=("STIXMAGIC_API_KEY_PROD", "STIXMAGIC_API_KEY"),
    )


def _resolve_session_secret(app_env: str) -> tuple[str, str | None]:
    if app_env == "development":
        return _resolve_exactly_one(
            config_name="session_secret",
            required=False,
            candidates=("SESSION_SECRET_DEV",),
        )

    return _resolve_exactly_one(
        config_name="session_secret",
        required=True,
        candidates=("SESSION_SECRET_PROD", "SESSION_SECRET"),
    )


def _resolve_miniapp_url(app_env: str) -> tuple[str, str | None]:
    if app_env == "development":
        return _resolve_exactly_one(
            config_name="miniapp_url",
            required=False,
            candidates=("MINIAPP_URL_DEV",),
        )
    return _resolve_exactly_one(
        config_name="miniapp_url",
        required=False,
        candidates=("MINIAPP_URL_PROD", "MINIAPP_URL"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = _normalize_env(os.environ.get("APP_ENV"))
    token, token_source = _resolve_token(app_env)
    api_key, api_key_source = _resolve_api_key(app_env)
    session_secret, session_secret_source = _resolve_session_secret(app_env)
    miniapp_url, miniapp_url_source = _resolve_miniapp_url(app_env)

    port_raw = _resolve_single("PORT") or "5000"
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ConfigError(f"PORT must be an integer. Got: {port_raw!r}") from exc

    return Settings(
        app_env=app_env,
        telegram_bot_token=token,
        telegram_token_source=token_source,
        api_key=api_key,
        api_key_source=api_key_source or "",
        session_secret=session_secret,
        session_secret_source=session_secret_source,
        miniapp_url=miniapp_url,
        miniapp_url_source=miniapp_url_source,
        port=port,
    )


def describe_expected_variables(app_env: str | None = None) -> list[str]:
    resolved_env = _normalize_env(app_env or os.environ.get("APP_ENV"))
    if resolved_env == "development":
        return [
            "APP_ENV=development",
            "DEV_BOT_TOKEN (preferred) or TELEGRAM_BOT_TOKEN_DEV",
            "STIXMAGIC_API_KEY_DEV",
            "SESSION_SECRET_DEV (optional)",
            "MINIAPP_URL_DEV (optional)",
        ]

    return [
        "APP_ENV=production",
        "TELEGRAM_BOT_TOKEN (preferred) or BOT_TOKEN",
        "STIXMAGIC_API_KEY_PROD (preferred) or STIXMAGIC_API_KEY",
        "SESSION_SECRET_PROD (preferred) or SESSION_SECRET",
        "MINIAPP_URL_PROD (optional) or MINIAPP_URL",
    ]

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_dotenv_loaded = False


def _ensure_dotenv() -> None:
    """
    Load environment variables from a .env file once for the running process.
    
    This function is idempotent and does nothing if the environment file has already been loaded.
    """
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
        """
        Builds the full public URL for the miniapp.
        
        Returns:
            The miniapp URL formed by concatenating `public_base_url` and `miniapp_path`, or an empty string if `public_base_url` is empty.
        """
        if not self.public_base_url:
            return ""
        return f"{self.public_base_url}{self.miniapp_path}"

    @property
    def miniapp_api_base_url(self) -> str:
        """
        Return the API base URL for the miniapp.
        
        Returns:
            The miniapp API base URL formed by appending "/miniapp" to `api_base_url`, or an empty string if `api_base_url` is empty.
        """
        if not self.api_base_url:
            return ""
        return f"{self.api_base_url}/miniapp"



def _strip_at_sign(value: str) -> str:
    """
    Remove a leading '@' character from a string if present.
    
    Parameters:
        value (str): The input string that may begin with '@'.
    
    Returns:
        str: The input string without a leading '@' if one was present, otherwise the original string.
    """
    return value[1:] if value.startswith("@") else value



def _infer_public_base_url() -> str:
    """
    Determine the public base URL for the application.
    
    Reads the STIXMAGIC_PUBLIC_BASE_URL environment variable, strips surrounding whitespace, and removes a trailing slash if present.
    
    Returns:
        str: The normalized public base URL or an empty string if the environment variable is unset or blank.
    """
    explicit = os.environ.get("STIXMAGIC_PUBLIC_BASE_URL", "").strip().rstrip("/")
    return explicit


def _env_suffix() -> str:
    """
    Map the APP_ENV environment value to a short uppercase suffix.
    
    Reads the `APP_ENV` environment variable (trimmed and lowercased) and returns:
    `"PROD"` if it equals `"production"`, `"TEST"` if it equals `"test"`, and
    `"DEV"` for any other value or if `APP_ENV` is unset.
    """
    mode = os.environ.get("APP_ENV", "development").strip().lower()
    return {"production": "PROD", "test": "TEST"}.get(mode, "DEV")


def _resolve_env(*names: str) -> str:
    """
    Get the first non-empty environment variable value from the provided names, after trimming whitespace.
    
    Parameters:
        names (str): Environment variable names in priority order.
    
    Returns:
        str: The first non-empty trimmed value found for the given names, or an empty string if none are set.
    """
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def get_settings() -> AppSettings:
    """
    Builds an AppSettings instance by reading and normalizing configuration from environment variables.
    
    Ensures a .env file is loaded (if present), derives an environment suffix from APP_ENV, computes base URLs and miniapp path defaults, and resolves required and optional settings from the environment.
    
    Returns:
        AppSettings: Configuration values populated from environment variables.
    
    Raises:
        ValueError: If no Telegram bot token is found in either `TELEGRAM_BOT_TOKEN` or `BOT_TOKEN_<suffix>`, where `<suffix>` is derived from `APP_ENV`.
    """
    _ensure_dotenv()

    suffix = _env_suffix()
    public_base_url = _infer_public_base_url()
    miniapp_path = os.environ.get("STIXMAGIC_MINIAPP_PATH", "/miniapp").strip() or "/miniapp"
    if not miniapp_path.startswith("/"):
        miniapp_path = f"/{miniapp_path}"

    api_base_url = f"{public_base_url}/api" if public_base_url else "/api"

    if suffix == "DEV":
        telegram_bot_token = _resolve_env("TELEGRAM_BOT_TOKEN", "DEV_BOT_TOKEN", "TELEGRAM_BOT_TOKEN_DEV", "BOT_TOKEN_DEV")
    else:
        telegram_bot_token = _resolve_env("TELEGRAM_BOT_TOKEN", f"BOT_TOKEN_{suffix}")

    if not telegram_bot_token:
        raise ValueError(
            f"Missing required telegram_bot_token. Set either TELEGRAM_BOT_TOKEN or BOT_TOKEN_{suffix} "
            f"(or DEV_BOT_TOKEN if in development) environment variable. Current APP_ENV suffix: {suffix}"
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
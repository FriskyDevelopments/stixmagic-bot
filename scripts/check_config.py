from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import ConfigError, get_settings


if __name__ == "__main__":
    try:
        settings = get_settings()
    except ConfigError as exc:
        raise SystemExit(f"CONFIG ERROR: {exc}") from exc

    print(
        "Configuration OK:",
        {
            "app_env": settings.app_env,
            "runtime_mode": "DEVELOPMENT" if settings.is_development else "PRODUCTION",
            "telegram_token_source": settings.telegram_token_source,
            "has_bot_token": bool(settings.telegram_bot_token),
            "has_api_key": bool(settings.api_key),
            "has_session_secret": bool(settings.session_secret),
            "has_miniapp_url": bool(settings.miniapp_url),
            "port": settings.port,
        },
    )

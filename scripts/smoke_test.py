from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import ConfigError, get_settings
from infra.db import init_db


if __name__ == "__main__":
    try:
        settings = get_settings()
    except ConfigError as exc:
        raise SystemExit(f"CONFIG ERROR: {exc}") from exc

    init_db()
    print(
        "Smoke test OK:",
        {
            "app_env": settings.app_env,
            "runtime_mode": "DEVELOPMENT" if settings.is_development else "PRODUCTION",
            "telegram_token_source": settings.telegram_token_source,
            "db_initialized": True,
            "miniapp_enabled": bool(settings.miniapp_url),
        },
    )

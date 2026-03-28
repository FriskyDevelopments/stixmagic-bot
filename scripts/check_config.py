from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stixmagic.settings import get_settings


if __name__ == "__main__":
    settings = get_settings()

    print(
        "Configuration OK:",
        {
            "has_bot_token": bool(settings.telegram_bot_token),
            "has_api_key": bool(settings.stixmagic_api_key),
            "has_webhook_secret": bool(settings.webhook_secret),
            "has_miniapp_url": bool(settings.miniapp_url),
            "bot_mode": settings.bot_mode,
            "db_path": settings.database_path,
        },
    )

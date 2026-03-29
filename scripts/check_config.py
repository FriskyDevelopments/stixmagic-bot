from pathlib import Path
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stixmagic.settings import get_settings


def _require(name: str, value: str) -> None:
    if not str(value).strip():
        raise SystemExit(f"Missing required configuration: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Stix Magic configuration.")
    parser.add_argument("--mode", choices=("ci", "production"), default="production")
    args = parser.parse_args()

    settings = get_settings()

    if args.mode != "ci":
        _require("telegram_bot_token", settings.telegram_bot_token)
        _require("stixmagic_api_key", settings.stixmagic_api_key)
        _require("webhook_secret", settings.webhook_secret)

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
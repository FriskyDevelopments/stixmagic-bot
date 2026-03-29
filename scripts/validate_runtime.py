#!/usr/bin/env python3
import argparse
import asyncio
import os
from pathlib import Path
import re
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOKEN_PATTERN = re.compile(r"\d{5,}:[A-Za-z0-9_-]{35,}")


def require_env(var_names: Iterable[str]) -> None:
    missing = [name for name in var_names if not os.environ.get(name, "").strip()]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")


def validate_token(env_name: str) -> str:
    raw_value = os.environ.get(env_name, "").strip()
    if not raw_value:
        raise SystemExit(f"{env_name} is required but was not provided.")

    if not TOKEN_PATTERN.fullmatch(raw_value):
        raise SystemExit(f"{env_name} does not look like a valid Telegram bot token.")

    return raw_value


def run_smoke_tests() -> None:
    from api import app
    from menus import build_keyboard, get_menu_text
    import main as bot_main

    client = app.test_client()
    response = client.get("/api/health")
    if response.status_code != 200:
        raise SystemExit(f"/api/health returned unexpected status {response.status_code}")

    payload = response.get_json()
    if not payload or not payload.get("ok"):
        raise SystemExit("/api/health did not return an ok payload")

    home_text = get_menu_text("home")
    if not home_text:
        raise SystemExit("menus.get_menu_text('home') returned empty text")

    keyboard = build_keyboard("home")
    if keyboard is None or not getattr(keyboard, "inline_keyboard", None):
        raise SystemExit("menus.build_keyboard('home') did not produce an inline keyboard")

    if not callable(bot_main.main):
        raise SystemExit("main.main is not callable")


async def telegram_get_me(token: str) -> None:
    from telegram import Bot

    bot = Bot(token=token)
    try:
        me = await bot.get_me()
    except Exception as exc:  # pragma: no cover - network dependent safeguard
        raise SystemExit(
            f"Telegram API smoke test failed with {type(exc).__name__}."
        ) from exc
    finally:
        await bot.close()

    if not getattr(me, "username", None):
        raise SystemExit("Telegram API smoke test succeeded but bot username was missing.")

    print(f"Telegram API smoke test passed for bot @{me.username}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Stix Magic runtime configuration.")
    parser.add_argument("--mode", choices=("ci", "production"), default="ci")
    parser.add_argument("--check-telegram", action="store_true")
    args = parser.parse_args()

    run_smoke_tests()

    if args.mode == "production":
        require_env(("STIXMAGIC_API_KEY", "TELEGRAM_WEBHOOK_SECRET"))
        from stixmagic.settings import get_settings
        settings = get_settings()
        token = settings.telegram_bot_token
        if not token or not TOKEN_PATTERN.fullmatch(token):
            raise SystemExit("telegram_bot_token is required and must be a valid Telegram bot token.")
        if args.check_telegram:
            asyncio.run(telegram_get_me(token))
    else:
        print("CI mode selected; production secrets are not required.")

    print("All checks passed.")


if __name__ == "__main__":
    main()
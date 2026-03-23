"""Telegram Mini App initData validation helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    """Raised when Telegram Mini App init data is missing or invalid."""


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> dict[str, Any]:
    if not init_data:
        raise TelegramInitDataError("Missing Telegram init data.")
    if not bot_token:
        raise TelegramInitDataError("Mini App auth cannot be verified without TELEGRAM_BOT_TOKEN.")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    their_hash = pairs.pop("hash", None)
    if not their_hash:
        raise TelegramInitDataError("Telegram init data is missing hash.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, their_hash):
        raise TelegramInitDataError("Telegram init data signature is invalid.")

    auth_date = int(pairs.get("auth_date", "0") or "0")
    if not auth_date:
        raise TelegramInitDataError("Telegram init data is missing auth_date.")
    if time.time() - auth_date > max_age_seconds:
        raise TelegramInitDataError("Telegram init data has expired.")

    user_raw = pairs.get("user")
    if not user_raw:
        raise TelegramInitDataError("Telegram init data is missing user.")

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise TelegramInitDataError("Telegram init data user payload is invalid.") from exc

    return {
        "auth_date": auth_date,
        "chat_type": pairs.get("chat_type"),
        "chat_instance": pairs.get("chat_instance"),
        "query_id": pairs.get("query_id"),
        "start_param": pairs.get("start_param"),
        "user": user,
    }

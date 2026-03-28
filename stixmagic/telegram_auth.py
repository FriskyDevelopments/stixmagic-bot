from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    """Raised when Telegram Mini App initData is missing or invalid."""



def _compute_hash(data: dict[str, str], bot_token: str) -> str:
    payload = {k: v for k, v in data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()



def validate_init_data(init_data: str, bot_token: str, *, max_age_seconds: int = 3600) -> dict:
    if not init_data:
        raise TelegramInitDataError("Missing Telegram init data")
    if not bot_token:
        raise TelegramInitDataError("Missing TELEGRAM_BOT_TOKEN")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    given_hash = parsed.get("hash", "")
    if not given_hash:
        raise TelegramInitDataError("Missing hash")

    expected_hash = _compute_hash(parsed, bot_token)
    if not hmac.compare_digest(given_hash, expected_hash):
        raise TelegramInitDataError("Invalid Telegram initData hash")

    auth_raw = parsed.get("auth_date", "").strip()
    if not auth_raw:
        raise TelegramInitDataError("Missing auth_date")
    try:
        auth_date = int(auth_raw)
    except ValueError as exc:
        raise TelegramInitDataError("Invalid auth_date") from exc
    if auth_date <= 0:
        raise TelegramInitDataError("Invalid auth_date")

    now = int(time.time())
    if now - auth_date > max_age_seconds:
        raise TelegramInitDataError("initData expired")

    user_raw = parsed.get("user", "")
    if not user_raw:
        raise TelegramInitDataError("Missing user")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise TelegramInitDataError("Invalid user payload") from exc

    return {
        "auth_date": auth_date,
        "chat_type": parsed.get("chat_type") or None,
        "chat_instance": parsed.get("chat_instance") or None,
        "query_id": parsed.get("query_id") or None,
        "start_param": parsed.get("start_param") or None,
        "user": user,
    }

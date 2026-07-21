from __future__ import annotations

import functools
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    """Raised when Telegram Mini App initData is missing or invalid."""



@functools.lru_cache(maxsize=1)
def _get_secret(bot_token: str) -> bytes:
    """Cache the secret key derived from the bot token."""
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def _compute_hash(data: dict[str, str], bot_token: str) -> str:
    """
    Compute the Telegram Web App verification HMAC-SHA256 hex digest for the given init data.
    
    Parameters:
    	data (dict[str, str]): Mapping of init_data key/value pairs; the optional 'hash' key, if present, will be ignored when computing the value.
    	bot_token (str): Telegram bot token used to derive the secret for the HMAC.
    
    Returns:
    	hex_digest (str): Lowercase hex digest of the HMAC-SHA256 verification hash.
    """
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if k != "hash")
    secret = _get_secret(bot_token)
    return hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()



def validate_init_data(init_data: str, bot_token: str, *, max_age_seconds: int = 3600) -> dict:
    """
    Validate Telegram Web App `init_data` (URL-encoded query string) and return selected parsed fields.
    
    Parameters:
        init_data (str): URL-encoded query string provided by Telegram Web App initData (contains `hash`, `auth_date`, `user`, etc.).
        bot_token (str): Telegram bot token used to verify the HMAC signature.
        max_age_seconds (int): Maximum allowed age of `auth_date` in seconds. Defaults to 3600.
    
    Returns:
        dict: Parsed and validated fields:
            - auth_date (int): UNIX epoch seconds from the `auth_date` field.
            - chat_type (str | None)
            - chat_instance (str | None)
            - query_id (str | None)
            - start_param (str | None)
            - user (dict): JSON-decoded `user` payload.
    
    Raises:
        TelegramInitDataError: If validation fails for any reason, including missing inputs, missing or invalid `hash`, invalid or expired `auth_date`, or missing/invalid `user` payload.
    """
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
"""
Tests for stixmagic/telegram_auth.py – Telegram Mini App initData validation.

Covers:
 - validate_init_data: valid data succeeds and returns expected fields
 - missing init_data raises TelegramInitDataError
 - missing bot_token raises TelegramInitDataError
 - missing hash raises TelegramInitDataError
 - invalid hash raises TelegramInitDataError
 - expired auth_date raises TelegramInitDataError
 - missing auth_date raises TelegramInitDataError
 - missing user field raises TelegramInitDataError
 - malformed user JSON raises TelegramInitDataError
 - start_param forwarded correctly
 - max_age_seconds=0 causes immediate expiry for non-zero auth_date
"""

import hashlib
import hmac
import json
import time
import unittest
from urllib.parse import urlencode

from stixmagic.telegram_auth import TelegramInitDataError, validate_init_data


def _build_init_data(
    bot_token: str,
    user: dict,
    auth_date: int | None = None,
    start_param: str | None = None,
    extra_pairs: dict | None = None,
    tamper_hash: bool = False,
) -> str:
    """
    Construct a valid (or optionally tampered) Telegram initData string.
    """
    if auth_date is None:
        auth_date = int(time.time())

    pairs: dict[str, str] = {
        "auth_date": str(auth_date),
        "user": json.dumps(user, separators=(",", ":")),
    }
    if start_param:
        pairs["start_param"] = start_param
    if extra_pairs:
        pairs.update(extra_pairs)

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    if tamper_hash:
        computed_hash = "0" * 64

    pairs["hash"] = computed_hash
    return urlencode(pairs)


FAKE_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh"
FAKE_USER = {"id": 42, "first_name": "Alice", "username": "alice"}


class TestValidateInitDataSuccess(unittest.TestCase):

    def test_valid_data_returns_dict(self):
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER)
        result = validate_init_data(init_data, FAKE_TOKEN)
        self.assertIsInstance(result, dict)

    def test_result_contains_user(self):
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER)
        result = validate_init_data(init_data, FAKE_TOKEN)
        self.assertIn("user", result)
        self.assertEqual(result["user"]["id"], 42)
        self.assertEqual(result["user"]["first_name"], "Alice")

    def test_result_contains_auth_date(self):
        ts = int(time.time())
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER, auth_date=ts)
        result = validate_init_data(init_data, FAKE_TOKEN)
        self.assertEqual(result["auth_date"], ts)

    def test_start_param_forwarded(self):
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER, start_param="create-pack")
        result = validate_init_data(init_data, FAKE_TOKEN)
        self.assertEqual(result["start_param"], "create-pack")

    def test_start_param_none_when_absent(self):
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER)
        result = validate_init_data(init_data, FAKE_TOKEN)
        self.assertIsNone(result["start_param"])

    def test_result_keys_present(self):
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER)
        result = validate_init_data(init_data, FAKE_TOKEN)
        for key in ("auth_date", "chat_type", "chat_instance", "query_id", "start_param", "user"):
            self.assertIn(key, result)

    def test_custom_max_age_seconds_accepted(self):
        ts = int(time.time()) - 100
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER, auth_date=ts)
        result = validate_init_data(init_data, FAKE_TOKEN, max_age_seconds=200)
        self.assertEqual(result["auth_date"], ts)


class TestValidateInitDataErrors(unittest.TestCase):

    def test_empty_init_data_raises(self):
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data("", FAKE_TOKEN)
        self.assertIn("Missing", str(ctx.exception))

    def test_empty_bot_token_raises(self):
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, "")
        self.assertIn("TELEGRAM_BOT_TOKEN", str(ctx.exception))

    def test_missing_hash_raises(self):
        # Build pairs without hash
        pairs = {
            "auth_date": str(int(time.time())),
            "user": json.dumps(FAKE_USER),
        }
        init_data = urlencode(pairs)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, FAKE_TOKEN)
        self.assertIn("hash", str(ctx.exception))

    def test_invalid_hash_raises(self):
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER, tamper_hash=True)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, FAKE_TOKEN)
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_wrong_bot_token_raises(self):
        init_data = _build_init_data("wrong_token:ABCDEF", FAKE_USER)
        with self.assertRaises(TelegramInitDataError):
            validate_init_data(init_data, FAKE_TOKEN)

    def test_expired_auth_date_raises(self):
        old_ts = int(time.time()) - 7200  # 2 hours ago
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER, auth_date=old_ts)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, FAKE_TOKEN, max_age_seconds=3600)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_missing_auth_date_raises(self):
        pairs = {
            "user": json.dumps(FAKE_USER),
        }
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", FAKE_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
        pairs["hash"] = computed_hash
        init_data = urlencode(pairs)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, FAKE_TOKEN)
        self.assertIn("auth_date", str(ctx.exception))

    def test_missing_user_field_raises(self):
        pairs = {
            "auth_date": str(int(time.time())),
        }
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", FAKE_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
        pairs["hash"] = computed_hash
        init_data = urlencode(pairs)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, FAKE_TOKEN)
        self.assertIn("user", str(ctx.exception))

    def test_malformed_user_json_raises(self):
        pairs = {
            "auth_date": str(int(time.time())),
            "user": "{not valid json",
        }
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", FAKE_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
        pairs["hash"] = computed_hash
        init_data = urlencode(pairs)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, FAKE_TOKEN)
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_auth_date_zero_raises(self):
        """auth_date=0 should be treated as missing/invalid."""
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER, auth_date=0)
        with self.assertRaises(TelegramInitDataError) as ctx:
            validate_init_data(init_data, FAKE_TOKEN)
        self.assertIn("auth_date", str(ctx.exception))

    def test_tma_is_subclass_of_value_error(self):
        """TelegramInitDataError must be a subclass of ValueError."""
        self.assertTrue(issubclass(TelegramInitDataError, ValueError))

    def test_future_auth_date_is_accepted(self):
        """A timestamp slightly in the future should still pass (clock skew)."""
        future_ts = int(time.time()) + 30
        init_data = _build_init_data(FAKE_TOKEN, FAKE_USER, auth_date=future_ts)
        # Should not raise with default max_age_seconds=3600
        result = validate_init_data(init_data, FAKE_TOKEN)
        self.assertEqual(result["auth_date"], future_ts)


if __name__ == "__main__":
    unittest.main()
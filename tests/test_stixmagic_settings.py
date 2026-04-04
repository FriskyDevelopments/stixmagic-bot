"""
Tests for stixmagic/settings.py – environment-driven configuration resolution.

Covers:
 - get_settings() with various env var combinations
 - AppSettings computed properties (miniapp_url, miniapp_api_base_url)
 - _infer_public_base_url: explicit var and fallback behavior
 - database_path defaults and overrides
 - bot_mode defaults and overrides
"""

import os
import unittest
from unittest.mock import patch


class TestGetSettings(unittest.TestCase):

    def _get_settings_with_env(self, env: dict):
        """Helper: run get_settings() with a controlled environment."""
        import stixmagic.settings as mod
        with patch.dict(os.environ, env, clear=True):
            return mod.get_settings()

    def test_basic_settings_loaded(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:abc",
            "TELEGRAM_BOT_USERNAME": "mybot",
            "STIXMAGIC_API_KEY": "secret",
            "STIXMAGIC_DB_PATH": "test.db",
            "STIXMAGIC_PUBLIC_BASE_URL": "https://example.com",
            "TELEGRAM_BOT_MODE": "polling",
        }
        s = self._get_settings_with_env(env)
        self.assertEqual(s.telegram_bot_token, "123:abc")
        self.assertEqual(s.telegram_bot_username, "mybot")
        self.assertEqual(s.stixmagic_api_key, "secret")
        self.assertEqual(s.database_path, "test.db")
        self.assertEqual(s.public_base_url, "https://example.com")
        self.assertEqual(s.bot_mode, "polling")

    def test_token_falls_back_to_env_suffix(self):
        env = {"APP_ENV": "development", "BOT_TOKEN_DEV": "123:abc"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.telegram_bot_token, "123:abc")

    def test_api_key_falls_back_to_env_suffix(self):
        env = {"APP_ENV": "production", "STIXMAGIC_API_KEY_PROD": "prod-key"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.stixmagic_api_key, "prod-key")

    def test_unsuffixed_token_precedence_over_fallback(self):
        env = {
            "APP_ENV": "production",
            "TELEGRAM_BOT_TOKEN": "111:direct",
            "BOT_TOKEN_PROD": "222:fallback",
        }
        s = self._get_settings_with_env(env)
        self.assertEqual(s.telegram_bot_token, "111:direct")

    def test_defaults_when_optional_vars_absent(self):
        env = {}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.telegram_bot_token, "")
        self.assertEqual(s.stixmagic_api_key, "")
        self.assertEqual(s.database_path, "bot.db")
        self.assertEqual(s.bot_mode, "polling")
        self.assertEqual(s.public_base_url, "")

    def test_database_path_default_is_bot_db(self):
        env = {}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.database_path, "bot.db")

    def test_database_path_override(self):
        env = {"STIXMAGIC_DB_PATH": "/data/myapp.db"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.database_path, "/data/myapp.db")

    def test_database_path_empty_string_falls_back_to_default(self):
        env = {"STIXMAGIC_DB_PATH": ""}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.database_path, "bot.db")

    def test_bot_mode_default_is_polling(self):
        env = {}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.bot_mode, "polling")

    def test_bot_mode_override(self):
        env = {"TELEGRAM_BOT_MODE": "webhook"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.bot_mode, "webhook")

    def test_bot_mode_normalized_to_lowercase(self):
        env = {"TELEGRAM_BOT_MODE": "POLLING"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.bot_mode, "polling")

    def test_bot_mode_empty_falls_back_to_polling(self):
        env = {"TELEGRAM_BOT_MODE": ""}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.bot_mode, "polling")

    def test_miniapp_path_default(self):
        env = {}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.miniapp_path, "/miniapp")

    def test_miniapp_path_override(self):
        env = {"STIXMAGIC_MINIAPP_PATH": "/app"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.miniapp_path, "/app")

    def test_webhook_url_and_secret_empty_by_default(self):
        env = {}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.webhook_url, "")
        self.assertEqual(s.webhook_secret, "")

    def test_webhook_url_set(self):
        env = {"TELEGRAM_WEBHOOK_URL": "https://example.com/webhook"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.webhook_url, "https://example.com/webhook")

    def test_bot_username_strips_at_sign(self):
        env = {"TELEGRAM_BOT_USERNAME": "@mybot"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.telegram_bot_username, "mybot")

    def test_bot_username_without_at_sign(self):
        env = {"TELEGRAM_BOT_USERNAME": "mybot"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.telegram_bot_username, "mybot")

    def test_bot_username_missing_returns_empty(self):
        """Missing TELEGRAM_BOT_USERNAME should return empty string (fail-closed but non-crashing)."""
        env = {}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.telegram_bot_username, "")

    def test_public_base_url_trailing_slash_stripped(self):
        env = {"STIXMAGIC_PUBLIC_BASE_URL": "https://example.com/"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.public_base_url, "https://example.com")

    def test_public_base_url_ignores_replit_domains(self):
        env = {"REPLIT_DOMAINS": "myapp.replit.app,secondary.replit.app"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.public_base_url, "")

    def test_public_base_url_explicit_set(self):
        env = {"STIXMAGIC_PUBLIC_BASE_URL": "https://custom.com"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.public_base_url, "https://custom.com")

    def test_api_base_url_constructed_from_public_base_url(self):
        env = {"STIXMAGIC_PUBLIC_BASE_URL": "https://example.com"}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.api_base_url, "https://example.com/api")

    def test_api_base_url_fallback_when_no_public_base(self):
        env = {}
        s = self._get_settings_with_env(env)
        self.assertEqual(s.api_base_url, "/api")

    def test_settings_is_frozen(self):
        env = {"TELEGRAM_BOT_TOKEN": "123:abc"}
        s = self._get_settings_with_env(env)
        with self.assertRaises((AttributeError, TypeError)):
            s.telegram_bot_token = "mutated"


class TestAppSettingsProperties(unittest.TestCase):

    def _make_settings(self, **kwargs):
        from stixmagic.settings import AppSettings
        defaults = dict(
            telegram_bot_token="tok",
            telegram_bot_username="bot",
            stixmagic_api_key="key",
            database_path="bot.db",
            public_base_url="https://example.com",
            api_base_url="https://example.com/api",
            miniapp_path="/miniapp",
            bot_mode="polling",
            webhook_url="",
            webhook_secret="",
        )
        defaults.update(kwargs)
        return AppSettings(**defaults)

    def test_miniapp_url_computed(self):
        s = self._make_settings(public_base_url="https://example.com", miniapp_path="/miniapp")
        self.assertEqual(s.miniapp_url, "https://example.com/miniapp")

    def test_miniapp_url_empty_when_no_public_base(self):
        s = self._make_settings(public_base_url="", api_base_url="/api")
        self.assertEqual(s.miniapp_url, "")

    def test_miniapp_api_base_url_computed(self):
        s = self._make_settings(api_base_url="https://example.com/api")
        self.assertEqual(s.miniapp_api_base_url, "https://example.com/api/miniapp")

    def test_miniapp_api_base_url_empty_when_no_api_base(self):
        s = self._make_settings(api_base_url="")
        self.assertEqual(s.miniapp_api_base_url, "")

    def test_custom_miniapp_path(self):
        s = self._make_settings(public_base_url="https://example.com", miniapp_path="/app")
        self.assertEqual(s.miniapp_url, "https://example.com/app")


if __name__ == "__main__":
    unittest.main()
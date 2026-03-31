import importlib
import os
import unittest
from unittest.mock import patch


class RuntimeConfigTests(unittest.TestCase):
    def _get_settings(self, env: dict[str, str]):
        with patch.dict(os.environ, env, clear=True):
            mod = importlib.import_module("config.runtime")
            importlib.reload(mod)
            mod.get_settings.cache_clear()
            return mod, mod.get_settings()

    def _assert_config_error(self, env: dict[str, str]):
        with patch.dict(os.environ, env, clear=True):
            mod = importlib.import_module("config.runtime")
            importlib.reload(mod)
            mod.get_settings.cache_clear()
            with self.assertRaises(mod.ConfigError):
                mod.get_settings()

    def test_development_requires_development_token(self):
        self._assert_config_error({"APP_ENV": "development", "STIXMAGIC_API_KEY_DEV": "dev-key"})

    def test_development_rejects_production_token_vars(self):
        self._assert_config_error(
            {
                "APP_ENV": "development",
                "DEV_BOT_TOKEN": "12345:abcde_token",
                "TELEGRAM_BOT_TOKEN": "99999:prod_token",
                "STIXMAGIC_API_KEY_DEV": "dev-key",
            }
        )

    def test_development_happy_path(self):
        _, s = self._get_settings(
            {
                "APP_ENV": "development",
                "DEV_BOT_TOKEN": "12345:abcde_token",
                "STIXMAGIC_API_KEY_DEV": "dev-key",
                "PORT": "5001",
            }
        )
        self.assertTrue(s.is_development)
        self.assertEqual(s.telegram_token_source, "DEV_BOT_TOKEN")
        self.assertEqual(s.port, 5001)

    def test_production_happy_path(self):
        _, s = self._get_settings(
            {
                "APP_ENV": "production",
                "TELEGRAM_BOT_TOKEN": "54321:prod_token",
                "STIXMAGIC_API_KEY_PROD": "prod-key",
                "SESSION_SECRET_PROD": "prod-secret",
            }
        )
        self.assertTrue(s.is_production)
        self.assertEqual(s.telegram_token_source, "TELEGRAM_BOT_TOKEN")

    def test_production_requires_session_secret(self):
        self._assert_config_error(
            {
                "APP_ENV": "production",
                "TELEGRAM_BOT_TOKEN": "54321:prod_token",
                "STIXMAGIC_API_KEY_PROD": "prod-key",
            }
        )

    def test_ambiguous_aliases_fail(self):
        self._assert_config_error(
            {
                "APP_ENV": "production",
                "TELEGRAM_BOT_TOKEN": "54321:prod_token",
                "BOT_TOKEN": "54321:prod_token",
                "STIXMAGIC_API_KEY_PROD": "prod-key",
                "SESSION_SECRET_PROD": "prod-secret",
            }
        )


if __name__ == "__main__":
    unittest.main()

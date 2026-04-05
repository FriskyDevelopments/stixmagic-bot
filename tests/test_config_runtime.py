"""
Tests for config/runtime.py – new runtime configuration module.

Covers:
 - _normalize_env: valid envs, defaults, invalid value raises ConfigError
 - _env_suffix: development/production/test mapping
 - _env_candidates: generates suffixed + base candidates
 - _resolve_optional: finds suffixed, falls back to base, returns default
 - _resolve_required: alias priority, env candidates, raises ConfigError
 - _validate_token: valid token extracts, invalid raises ConfigError
 - get_settings: full integration with environment setup
 - get_settings: production without session_secret raises ConfigError
 - get_settings: uses TELEGRAM_BOT_TOKEN alias
 - describe_expected_variables: returns correct variable list
 - Settings.is_development / is_production properties
"""

import os
import sys
import unittest
from unittest.mock import patch

# Ensure project root is importable
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


VALID_DEV_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
VALID_PROD_TOKEN = "987654:XYZ-MNO4567pqRst-uvw89A1b234cd56"


def _fresh_get_settings():
    """Import get_settings with cache cleared to pick up env changes."""
    import config.runtime as rt
    rt.get_settings.cache_clear()
    return rt.get_settings


class TestNormalizeEnv(unittest.TestCase):
    """Tests for config.runtime._normalize_env."""

    def setUp(self):
        import config.runtime as rt
        self.fn = rt._normalize_env

    def test_development_is_valid(self):
        self.assertEqual(self.fn("development"), "development")

    def test_production_is_valid(self):
        self.assertEqual(self.fn("production"), "production")

    def test_test_is_valid(self):
        self.assertEqual(self.fn("test"), "test")

    def test_none_defaults_to_development(self):
        self.assertEqual(self.fn(None), "development")

    def test_empty_string_defaults_to_development(self):
        self.assertEqual(self.fn(""), "development")

    def test_uppercase_normalized(self):
        self.assertEqual(self.fn("DEVELOPMENT"), "development")
        self.assertEqual(self.fn("PRODUCTION"), "production")

    def test_mixed_case_normalized(self):
        self.assertEqual(self.fn("Development"), "development")

    def test_invalid_raises_config_error(self):
        from config.runtime import ConfigError
        with self.assertRaises(ConfigError) as ctx:
            self.fn("staging")
        self.assertIn("APP_ENV", str(ctx.exception))

    def test_invalid_value_in_error_message(self):
        from config.runtime import ConfigError
        with self.assertRaises(ConfigError) as ctx:
            self.fn("prod")
        self.assertIn("prod", str(ctx.exception))

    def test_whitespace_stripped(self):
        self.assertEqual(self.fn("  development  "), "development")


class TestEnvSuffix(unittest.TestCase):
    """Tests for config.runtime._env_suffix."""

    def setUp(self):
        from config.runtime import _env_suffix
        self.fn = _env_suffix

    def test_development_returns_DEV(self):
        self.assertEqual(self.fn("development"), "DEV")

    def test_production_returns_PROD(self):
        self.assertEqual(self.fn("production"), "PROD")

    def test_test_returns_TEST(self):
        self.assertEqual(self.fn("test"), "TEST")


class TestEnvCandidates(unittest.TestCase):
    """Tests for config.runtime._env_candidates."""

    def setUp(self):
        from config.runtime import _env_candidates
        self.fn = _env_candidates

    def test_development_generates_DEV_and_base(self):
        result = self.fn("BOT_TOKEN", "development")
        self.assertEqual(result, ["BOT_TOKEN_DEV", "BOT_TOKEN"])

    def test_production_generates_PROD_and_base(self):
        result = self.fn("STIXMAGIC_API_KEY", "production")
        self.assertEqual(result, ["STIXMAGIC_API_KEY_PROD", "STIXMAGIC_API_KEY"])

    def test_test_generates_TEST_and_base(self):
        result = self.fn("SESSION_SECRET", "test")
        self.assertEqual(result, ["SESSION_SECRET_TEST", "SESSION_SECRET"])

    def test_suffixed_name_comes_first(self):
        result = self.fn("MINIAPP_URL", "development")
        self.assertEqual(result[0], "MINIAPP_URL_DEV")


class TestResolveOptional(unittest.TestCase):
    """Tests for config.runtime._resolve_optional."""

    def setUp(self):
        from config.runtime import _resolve_optional
        self.fn = _resolve_optional

    def test_returns_suffixed_var_when_set(self):
        with patch.dict(os.environ, {"SESSION_SECRET_DEV": "dev-secret"}, clear=False):
            result = self.fn("SESSION_SECRET", "development")
        self.assertEqual(result, "dev-secret")

    def test_falls_back_to_base_when_suffixed_absent(self):
        env = {"SESSION_SECRET": "base-secret"}
        # Ensure suffixed not present
        with patch.dict(os.environ, env, clear=False):
            # Remove DEV variant if present
            env_copy = os.environ.copy()
            env_copy.pop("SESSION_SECRET_DEV", None)
            env_copy["SESSION_SECRET"] = "base-secret"
            with patch.dict(os.environ, env_copy, clear=True):
                result = self.fn("SESSION_SECRET", "development")
        self.assertEqual(result, "base-secret")

    def test_returns_default_when_nothing_set(self):
        with patch.dict(os.environ, {}, clear=True):
            result = self.fn("SESSION_SECRET", "development", default="fallback")
        self.assertEqual(result, "fallback")

    def test_empty_string_default(self):
        with patch.dict(os.environ, {}, clear=True):
            result = self.fn("SESSION_SECRET", "development")
        self.assertEqual(result, "")

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"SESSION_SECRET_DEV": "  trimmed  "}, clear=False):
            result = self.fn("SESSION_SECRET", "development")
        self.assertEqual(result, "trimmed")

    def test_production_uses_prod_suffix(self):
        with patch.dict(os.environ, {"MINIAPP_URL_PROD": "https://prod.example.com"}, clear=False):
            result = self.fn("MINIAPP_URL", "production")
        self.assertEqual(result, "https://prod.example.com")


class TestResolveRequired(unittest.TestCase):
    """Tests for config.runtime._resolve_required."""

    def setUp(self):
        from config.runtime import _resolve_required
        self.fn = _resolve_required

    def test_alias_takes_priority_over_suffixed(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "alias-token",
            "BOT_TOKEN_DEV": "dev-token",
        }
        with patch.dict(os.environ, env, clear=True):
            result = self.fn("BOT_TOKEN", "development", aliases=("TELEGRAM_BOT_TOKEN",))
        self.assertEqual(result, "alias-token")

    def test_suffixed_var_found(self):
        with patch.dict(os.environ, {"BOT_TOKEN_DEV": "dev-token"}, clear=True):
            result = self.fn("BOT_TOKEN", "development")
        self.assertEqual(result, "dev-token")

    def test_base_var_as_fallback(self):
        with patch.dict(os.environ, {"BOT_TOKEN": "base-token"}, clear=True):
            result = self.fn("BOT_TOKEN", "development")
        self.assertEqual(result, "base-token")

    def test_raises_config_error_when_nothing_set(self):
        from config.runtime import ConfigError
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                self.fn("BOT_TOKEN", "development")
        self.assertIn("BOT_TOKEN", str(ctx.exception))

    def test_error_message_lists_expected_vars(self):
        from config.runtime import ConfigError
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                self.fn("BOT_TOKEN", "development")
        msg = str(ctx.exception)
        self.assertIn("BOT_TOKEN_DEV", msg)

    def test_strips_whitespace_from_value(self):
        with patch.dict(os.environ, {"BOT_TOKEN_DEV": "  spaced-token  "}, clear=True):
            result = self.fn("BOT_TOKEN", "development")
        self.assertEqual(result, "spaced-token")

    def test_production_suffixed_var(self):
        with patch.dict(os.environ, {"STIXMAGIC_API_KEY_PROD": "prod-key"}, clear=True):
            result = self.fn("STIXMAGIC_API_KEY", "production")
        self.assertEqual(result, "prod-key")


class TestValidateToken(unittest.TestCase):
    """Tests for config.runtime._validate_token."""

    def setUp(self):
        from config.runtime import _validate_token
        self.fn = _validate_token

    def test_valid_token_returns_extracted_token(self):
        result = self.fn(VALID_DEV_TOKEN)
        # Should return the token portion matched
        self.assertIn(":", result)

    def test_valid_token_with_prefix_text(self):
        result = self.fn(f"Bearer {VALID_DEV_TOKEN}")
        self.assertIn(":", result)

    def test_invalid_token_raises_config_error(self):
        from config.runtime import ConfigError
        with self.assertRaises(ConfigError) as ctx:
            self.fn("not-a-valid-token")
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_empty_token_raises_config_error(self):
        from config.runtime import ConfigError
        with self.assertRaises(ConfigError):
            self.fn("")

    def test_token_without_colon_raises_config_error(self):
        from config.runtime import ConfigError
        with self.assertRaises(ConfigError):
            self.fn("1234567890ABCDEFabcdef")

    def test_token_with_only_digits_raises_config_error(self):
        from config.runtime import ConfigError
        with self.assertRaises(ConfigError):
            self.fn("123456789")

    def test_realistic_long_token(self):
        token = "7890123456:AAEioTzh-abcDEFghijklmnopqrstuvwXYZ12"
        result = self.fn(token)
        self.assertTrue(result.startswith("7890123456:"))


class TestGetSettings(unittest.TestCase):
    """Integration tests for config.runtime.get_settings."""

    def _get_settings(self, env_vars):
        """Call get_settings with a clean environment."""
        import config.runtime as rt
        rt.get_settings.cache_clear()
        with patch.dict(os.environ, env_vars, clear=True):
            return rt.get_settings()

    def tearDown(self):
        import config.runtime as rt
        rt.get_settings.cache_clear()

    def test_development_config(self):
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        })
        self.assertEqual(settings.app_env, "development")
        self.assertTrue(settings.is_development)
        self.assertFalse(settings.is_production)

    def test_production_config_with_session_secret(self):
        settings = self._get_settings({
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": VALID_PROD_TOKEN,
            "STIXMAGIC_API_KEY_PROD": "prod-api-key",
            "SESSION_SECRET_PROD": "prod-session-secret",
        })
        self.assertEqual(settings.app_env, "production")
        self.assertFalse(settings.is_development)
        self.assertTrue(settings.is_production)

    def test_production_without_session_secret_raises(self):
        from config.runtime import ConfigError
        import config.runtime as rt
        rt.get_settings.cache_clear()
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": VALID_PROD_TOKEN,
            "STIXMAGIC_API_KEY_PROD": "prod-api-key",
        }, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                rt.get_settings()
            self.assertIn("SESSION_SECRET", str(ctx.exception))

    def test_telegram_bot_token_alias_accepted(self):
        settings = self._get_settings({
            "APP_ENV": "development",
            "TELEGRAM_BOT_TOKEN": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        })
        self.assertIn(":", settings.telegram_bot_token)

    def test_test_environment_config(self):
        settings = self._get_settings({
            "APP_ENV": "test",
            "BOT_TOKEN_TEST": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_TEST": "test-api-key",
        })
        self.assertEqual(settings.app_env, "test")

    def test_invalid_app_env_raises(self):
        from config.runtime import ConfigError
        import config.runtime as rt
        rt.get_settings.cache_clear()
        with patch.dict(os.environ, {
            "APP_ENV": "invalid_env",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        }, clear=True):
            with self.assertRaises(ConfigError):
                rt.get_settings()

    def test_missing_bot_token_raises(self):
        from config.runtime import ConfigError
        import config.runtime as rt
        rt.get_settings.cache_clear()
        with patch.dict(os.environ, {
            "APP_ENV": "development",
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        }, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                rt.get_settings()
            self.assertIn("BOT_TOKEN", str(ctx.exception))

    def test_missing_api_key_raises(self):
        from config.runtime import ConfigError
        import config.runtime as rt
        rt.get_settings.cache_clear()
        with patch.dict(os.environ, {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
        }, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                rt.get_settings()
            self.assertIn("STIXMAGIC_API_KEY", str(ctx.exception))

    def test_invalid_token_format_raises(self):
        from config.runtime import ConfigError
        import config.runtime as rt
        rt.get_settings.cache_clear()
        with patch.dict(os.environ, {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": "not-a-valid-token",
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        }, clear=True):
            with self.assertRaises(ConfigError):
                rt.get_settings()

    def test_optional_miniapp_url_absent(self):
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        })
        self.assertEqual(settings.miniapp_url, "")

    def test_optional_miniapp_url_present(self):
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
            "MINIAPP_URL_DEV": "https://example.com/miniapp",
        })
        self.assertEqual(settings.miniapp_url, "https://example.com/miniapp")

    def test_optional_session_secret_absent_in_development(self):
        """Development allows missing session_secret."""
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        })
        self.assertEqual(settings.session_secret, "")

    def test_port_defaults_to_5000(self):
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        })
        self.assertEqual(settings.port, 5000)

    def test_port_can_be_overridden(self):
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
            "PORT": "8080",
        })
        self.assertEqual(settings.port, 8080)

    def test_settings_is_frozen_dataclass(self):
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        })
        with self.assertRaises((AttributeError, TypeError)):
            settings.app_env = "production"  # frozen dataclass should raise

    def test_base_api_key_var_accepted_in_development(self):
        """STIXMAGIC_API_KEY (base) should be accepted as fallback for development."""
        settings = self._get_settings({
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": VALID_DEV_TOKEN,
            "STIXMAGIC_API_KEY": "fallback-api-key",
        })
        self.assertEqual(settings.api_key, "fallback-api-key")

    def test_base_session_secret_accepted_in_production(self):
        """SESSION_SECRET (base) should be accepted as fallback for production."""
        settings = self._get_settings({
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": VALID_PROD_TOKEN,
            "STIXMAGIC_API_KEY_PROD": "prod-api-key",
            "SESSION_SECRET": "base-secret",
        })
        self.assertEqual(settings.session_secret, "base-secret")


class TestSettingsProperties(unittest.TestCase):
    """Tests for Settings.is_development and is_production properties."""

    def _make_settings(self, app_env):
        from config.runtime import Settings
        return Settings(
            app_env=app_env,
            telegram_bot_token="123:abc",
            api_key="key",
            session_secret="secret",
            miniapp_url="",
            port=5000,
        )

    def test_is_development_true_when_development(self):
        s = self._make_settings("development")
        self.assertTrue(s.is_development)
        self.assertFalse(s.is_production)

    def test_is_production_true_when_production(self):
        s = self._make_settings("production")
        self.assertTrue(s.is_production)
        self.assertFalse(s.is_development)

    def test_test_env_neither_dev_nor_prod(self):
        s = self._make_settings("test")
        self.assertFalse(s.is_development)
        self.assertFalse(s.is_production)


class TestDescribeExpectedVariables(unittest.TestCase):
    """Tests for config.runtime.describe_expected_variables."""

    def setUp(self):
        from config.runtime import describe_expected_variables
        self.fn = describe_expected_variables

    def test_returns_list(self):
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
            result = self.fn()
        self.assertIsInstance(result, list)

    def test_development_lists_dev_suffix_vars(self):
        result = self.fn("development")
        combined = "\n".join(result)
        self.assertIn("BOT_TOKEN_DEV", combined)
        self.assertIn("STIXMAGIC_API_KEY_DEV", combined)

    def test_production_lists_prod_suffix_vars(self):
        result = self.fn("production")
        combined = "\n".join(result)
        self.assertIn("BOT_TOKEN_PROD", combined)
        self.assertIn("STIXMAGIC_API_KEY_PROD", combined)

    def test_test_env_lists_test_suffix_vars(self):
        result = self.fn("test")
        combined = "\n".join(result)
        self.assertIn("BOT_TOKEN_TEST", combined)

    def test_includes_miniapp_url(self):
        result = self.fn("development")
        combined = "\n".join(result)
        self.assertIn("MINIAPP_URL", combined)

    def test_includes_session_secret(self):
        result = self.fn("development")
        combined = "\n".join(result)
        self.assertIn("SESSION_SECRET", combined)

    def test_default_env_from_os_environ(self):
        """When no arg given, uses APP_ENV from environment."""
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            import config.runtime as rt
            result = rt.describe_expected_variables()
        combined = "\n".join(result)
        self.assertIn("PROD", combined)


if __name__ == "__main__":
    unittest.main()
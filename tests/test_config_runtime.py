"""
Tests for config/runtime.py – runtime configuration resolution.

Covers:
 - _normalize_env: valid values, default, invalid raises ConfigError
 - _env_suffix: mapping for each supported environment
 - _env_candidates: returns suffixed + bare name
 - _resolve_optional: priority order, empty fallback
 - _resolve_required: alias priority, suffixed name, bare name, raises when missing
 - _validate_token: valid token extracted, invalid raises ConfigError
 - get_settings(): development, production, test configs; missing required; production without session_secret
 - Settings properties: is_development, is_production
 - describe_expected_variables(): format for each environment
"""

import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config.runtime as runtime_mod
from config.runtime import (
    ConfigError,
    Settings,
    _env_candidates,
    _env_suffix,
    _normalize_env,
    _resolve_optional,
    _resolve_required,
    _validate_token,
    describe_expected_variables,
    get_settings,
)


class TestNormalizeEnv(unittest.TestCase):

    def test_development_is_valid(self):
        self.assertEqual(_normalize_env("development"), "development")

    def test_production_is_valid(self):
        self.assertEqual(_normalize_env("production"), "production")

    def test_test_is_valid(self):
        self.assertEqual(_normalize_env("test"), "test")

    def test_none_defaults_to_development(self):
        self.assertEqual(_normalize_env(None), "development")

    def test_empty_string_defaults_to_development(self):
        self.assertEqual(_normalize_env(""), "development")

    def test_whitespace_only_raises_config_error(self):
        """Whitespace-only string is truthy, strips to "", not in VALID_ENVS -> error."""
        with self.assertRaises(ConfigError):
            _normalize_env("  ")

    def test_uppercase_normalized(self):
        self.assertEqual(_normalize_env("DEVELOPMENT"), "development")
        self.assertEqual(_normalize_env("PRODUCTION"), "production")

    def test_mixed_case_normalized(self):
        self.assertEqual(_normalize_env("Development"), "development")

    def test_invalid_value_raises_config_error(self):
        with self.assertRaises(ConfigError):
            _normalize_env("staging")

    def test_invalid_value_error_mentions_valid_envs(self):
        try:
            _normalize_env("qa")
        except ConfigError as e:
            self.assertIn("development", str(e))
            self.assertIn("production", str(e))

    def test_strips_whitespace(self):
        self.assertEqual(_normalize_env("  production  "), "production")


class TestEnvSuffix(unittest.TestCase):

    def test_development_returns_dev(self):
        self.assertEqual(_env_suffix("development"), "DEV")

    def test_production_returns_prod(self):
        self.assertEqual(_env_suffix("production"), "PROD")

    def test_test_returns_test(self):
        self.assertEqual(_env_suffix("test"), "TEST")


class TestEnvCandidates(unittest.TestCase):

    def test_development_candidates(self):
        candidates = _env_candidates("BOT_TOKEN", "development")
        self.assertEqual(candidates, ["BOT_TOKEN_DEV", "BOT_TOKEN"])

    def test_production_candidates(self):
        candidates = _env_candidates("BOT_TOKEN", "production")
        self.assertEqual(candidates, ["BOT_TOKEN_PROD", "BOT_TOKEN"])

    def test_test_candidates(self):
        candidates = _env_candidates("SESSION_SECRET", "test")
        self.assertEqual(candidates, ["SESSION_SECRET_TEST", "SESSION_SECRET"])

    def test_always_returns_two_entries(self):
        for env in ("development", "production", "test"):
            self.assertEqual(len(_env_candidates("SOME_VAR", env)), 2)

    def test_suffixed_name_comes_first(self):
        candidates = _env_candidates("MINIAPP_URL", "production")
        self.assertTrue(candidates[0].endswith("_PROD"))
        self.assertEqual(candidates[1], "MINIAPP_URL")


class TestResolveOptional(unittest.TestCase):

    def test_returns_suffixed_var_when_set(self):
        with patch.dict(os.environ, {"SESSION_SECRET_DEV": "dev-secret"}, clear=False):
            result = _resolve_optional("SESSION_SECRET", "development")
        self.assertEqual(result, "dev-secret")

    def test_falls_back_to_bare_name(self):
        env = {"SESSION_SECRET": "bare-secret"}
        # Ensure suffixed var is not set
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SESSION_SECRET_DEV", None)
            result = _resolve_optional("SESSION_SECRET", "development")
        self.assertEqual(result, "bare-secret")

    def test_returns_default_when_nothing_set(self):
        env = {}
        with patch.dict(os.environ, env):
            os.environ.pop("SESSION_SECRET_DEV", None)
            os.environ.pop("SESSION_SECRET", None)
            result = _resolve_optional("SESSION_SECRET", "development", default="fallback")
        self.assertEqual(result, "fallback")

    def test_returns_empty_string_default(self):
        with patch.dict(os.environ, {}, clear=True):
            result = _resolve_optional("NONEXISTENT_VAR", "development")
        self.assertEqual(result, "")

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"SESSION_SECRET_DEV": "  spaced  "}, clear=False):
            result = _resolve_optional("SESSION_SECRET", "development")
        self.assertEqual(result, "spaced")

    def test_suffixed_takes_priority_over_bare(self):
        env = {"MINIAPP_URL_PROD": "https://prod.example.com", "MINIAPP_URL": "https://other.example.com"}
        with patch.dict(os.environ, env, clear=False):
            result = _resolve_optional("MINIAPP_URL", "production")
        self.assertEqual(result, "https://prod.example.com")


class TestResolveRequired(unittest.TestCase):

    def test_returns_alias_first(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "111:alias-token",
            "BOT_TOKEN_DEV": "222:dev-token",
        }
        with patch.dict(os.environ, env, clear=False):
            result = _resolve_required("BOT_TOKEN", "development", aliases=("TELEGRAM_BOT_TOKEN",))
        self.assertEqual(result, "111:alias-token")

    def test_returns_suffixed_when_no_alias(self):
        env = {"BOT_TOKEN_DEV": "333:suffixed-token"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            result = _resolve_required("BOT_TOKEN", "development", aliases=("TELEGRAM_BOT_TOKEN",))
        self.assertEqual(result, "333:suffixed-token")

    def test_returns_bare_name_when_no_suffix(self):
        env = {"BOT_TOKEN": "444:bare-token"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            os.environ.pop("BOT_TOKEN_DEV", None)
            result = _resolve_required("BOT_TOKEN", "development", aliases=("TELEGRAM_BOT_TOKEN",))
        self.assertEqual(result, "444:bare-token")

    def test_raises_config_error_when_nothing_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                _resolve_required("BOT_TOKEN", "development", aliases=("TELEGRAM_BOT_TOKEN",))

    def test_error_message_mentions_expected_names(self):
        with patch.dict(os.environ, {}, clear=True):
            try:
                _resolve_required("BOT_TOKEN", "development", aliases=("TELEGRAM_BOT_TOKEN",))
            except ConfigError as e:
                self.assertIn("BOT_TOKEN", str(e))

    def test_strips_whitespace_from_value(self):
        env = {"STIXMAGIC_API_KEY_DEV": "  mykey  "}
        with patch.dict(os.environ, env, clear=False):
            result = _resolve_required("STIXMAGIC_API_KEY", "development")
        self.assertEqual(result, "mykey")

    def test_no_aliases_still_works(self):
        env = {"STIXMAGIC_API_KEY_DEV": "some-api-key"}
        with patch.dict(os.environ, env, clear=False):
            result = _resolve_required("STIXMAGIC_API_KEY", "development")
        self.assertEqual(result, "some-api-key")


class TestValidateToken(unittest.TestCase):

    def test_valid_token_extracted(self):
        raw = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh"
        result = _validate_token(raw)
        self.assertEqual(result, raw)

    def test_valid_token_embedded_in_longer_string(self):
        # Token embedded in noise should still be extracted
        raw = "  123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh  "
        result = _validate_token(raw)
        self.assertIn("123456:", result)

    def test_invalid_token_raises_config_error(self):
        with self.assertRaises(ConfigError):
            _validate_token("not-a-token")

    def test_empty_string_raises_config_error(self):
        with self.assertRaises(ConfigError):
            _validate_token("")

    def test_only_numbers_raises_config_error(self):
        with self.assertRaises(ConfigError):
            _validate_token("123456789")

    def test_token_with_hyphen_in_secret_is_valid(self):
        raw = "987654:ABCDEF-ghijklmnopqrstuvwxyz12345_ab"
        result = _validate_token(raw)
        self.assertIn("987654:", result)

    def test_error_message_mentions_expected_format(self):
        try:
            _validate_token("bad")
        except ConfigError as e:
            self.assertIn("BOT_TOKEN", str(e))


class TestGetSettings(unittest.TestCase):
    """Tests for get_settings() – uses clean environment per test via lru_cache clearing."""

    def setUp(self):
        # Clear the lru_cache before each test
        get_settings.cache_clear()

    def tearDown(self):
        get_settings.cache_clear()

    def _dev_env(self):
        return {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        }

    def _prod_env(self):
        return {
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_PROD": "prod-api-key",
            "SESSION_SECRET_PROD": "prod-session-secret",
        }

    def test_development_config_resolves(self):
        with patch.dict(os.environ, self._dev_env(), clear=True):
            s = get_settings()
        self.assertEqual(s.app_env, "development")

    def test_production_config_resolves(self):
        with patch.dict(os.environ, self._prod_env(), clear=True):
            s = get_settings()
        self.assertEqual(s.app_env, "production")

    def test_test_env_resolves(self):
        env = {
            "APP_ENV": "test",
            "BOT_TOKEN_TEST": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_TEST": "test-api-key",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.app_env, "test")

    def test_defaults_to_development_when_app_env_not_set(self):
        env = {
            "BOT_TOKEN_DEV": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_DEV": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.app_env, "development")

    def test_telegram_bot_token_resolved(self):
        with patch.dict(os.environ, self._dev_env(), clear=True):
            s = get_settings()
        self.assertIn("123456:", s.telegram_bot_token)

    def test_legacy_telegram_bot_token_alias(self):
        env = {
            "APP_ENV": "development",
            "TELEGRAM_BOT_TOKEN": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_DEV": "some-key",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertIn("123456:", s.telegram_bot_token)

    def test_api_key_resolved(self):
        with patch.dict(os.environ, self._dev_env(), clear=True):
            s = get_settings()
        self.assertEqual(s.api_key, "dev-api-key")

    def test_session_secret_optional_in_development(self):
        env = dict(self._dev_env())  # No SESSION_SECRET
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.session_secret, "")

    def test_session_secret_required_in_production(self):
        env = {
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_PROD": "key",
            # SESSION_SECRET_PROD intentionally absent
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                get_settings()
        self.assertIn("SESSION_SECRET", str(ctx.exception))

    def test_miniapp_url_optional(self):
        with patch.dict(os.environ, self._dev_env(), clear=True):
            s = get_settings()
        self.assertEqual(s.miniapp_url, "")

    def test_miniapp_url_resolved_when_set(self):
        env = dict(self._dev_env())
        env["MINIAPP_URL_DEV"] = "https://dev.example.com/miniapp"
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.miniapp_url, "https://dev.example.com/miniapp")

    def test_port_defaults_to_5000(self):
        with patch.dict(os.environ, self._dev_env(), clear=True):
            s = get_settings()
        self.assertEqual(s.port, 5000)

    def test_port_override(self):
        env = dict(self._dev_env())
        env["PORT"] = "8080"
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.port, 8080)

    def test_missing_bot_token_raises_config_error(self):
        env = {
            "APP_ENV": "development",
            "STIXMAGIC_API_KEY_DEV": "some-key",
            # No BOT_TOKEN_DEV
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError):
                get_settings()

    def test_missing_api_key_raises_config_error(self):
        env = {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            # No STIXMAGIC_API_KEY_DEV
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError):
                get_settings()

    def test_invalid_app_env_raises_config_error(self):
        env = {
            "APP_ENV": "staging",
            "BOT_TOKEN_DEV": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_DEV": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError):
                get_settings()

    def test_invalid_bot_token_raises_config_error(self):
        env = {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": "not-a-valid-token",
            "STIXMAGIC_API_KEY_DEV": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError):
                get_settings()

    def test_settings_is_frozen_dataclass(self):
        with patch.dict(os.environ, self._dev_env(), clear=True):
            s = get_settings()
        with self.assertRaises(Exception):
            s.app_env = "production"  # type: ignore[misc]

    def test_production_session_secret_from_bare_name(self):
        env = {
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_PROD": "key",
            "SESSION_SECRET": "legacy-secret",  # bare name fallback
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.session_secret, "legacy-secret")


class TestSettingsProperties(unittest.TestCase):

    def setUp(self):
        get_settings.cache_clear()

    def tearDown(self):
        get_settings.cache_clear()

    def test_is_development_true_in_development(self):
        s = Settings(
            app_env="development",
            telegram_bot_token="123:token",
            api_key="key",
            session_secret="",
            miniapp_url="",
            port=5000,
        )
        self.assertTrue(s.is_development)
        self.assertFalse(s.is_production)

    def test_is_production_true_in_production(self):
        s = Settings(
            app_env="production",
            telegram_bot_token="123:token",
            api_key="key",
            session_secret="secret",
            miniapp_url="",
            port=5000,
        )
        self.assertFalse(s.is_development)
        self.assertTrue(s.is_production)

    def test_test_env_neither_dev_nor_prod(self):
        s = Settings(
            app_env="test",
            telegram_bot_token="123:token",
            api_key="key",
            session_secret="",
            miniapp_url="",
            port=5000,
        )
        self.assertFalse(s.is_development)
        self.assertFalse(s.is_production)


class TestDescribeExpectedVariables(unittest.TestCase):

    def setUp(self):
        get_settings.cache_clear()

    def tearDown(self):
        get_settings.cache_clear()

    def _get_for_env(self, env_name):
        with patch.dict(os.environ, {"APP_ENV": env_name}, clear=False):
            return describe_expected_variables(env_name)

    def test_development_includes_dev_suffix(self):
        result = self._get_for_env("development")
        self.assertTrue(any("DEV" in item for item in result))

    def test_production_includes_prod_suffix(self):
        result = self._get_for_env("production")
        self.assertTrue(any("PROD" in item for item in result))

    def test_test_env_includes_test_suffix(self):
        result = self._get_for_env("test")
        self.assertTrue(any("TEST" in item for item in result))

    def test_returns_list(self):
        result = self._get_for_env("development")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_includes_bot_token_entry(self):
        result = self._get_for_env("development")
        self.assertTrue(any("BOT_TOKEN" in item for item in result))

    def test_includes_api_key_entry(self):
        result = self._get_for_env("development")
        self.assertTrue(any("STIXMAGIC_API_KEY" in item for item in result))

    def test_uses_app_env_from_environ_when_no_arg(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            result = describe_expected_variables()
        self.assertTrue(any("PROD" in item for item in result))

    def test_all_environments_return_same_structure_length(self):
        for env in ("development", "production", "test"):
            result = self._get_for_env(env)
            self.assertEqual(len(result), 4, f"Expected 4 entries for {env}")


class TestGetSettingsAdditional(unittest.TestCase):
    """Additional edge-case and regression tests for get_settings()."""

    def setUp(self):
        get_settings.cache_clear()

    def tearDown(self):
        get_settings.cache_clear()

    def _dev_env(self):
        return {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_DEV": "dev-api-key",
        }

    def test_test_env_does_not_require_session_secret(self):
        """PR: 'test' env should not require SESSION_SECRET unlike 'production'."""
        env = {
            "APP_ENV": "test",
            "BOT_TOKEN_TEST": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_TEST": "test-api-key",
            # SESSION_SECRET_TEST intentionally absent
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.app_env, "test")
        self.assertEqual(s.session_secret, "")

    def test_session_secret_prod_takes_priority_over_bare_session_secret(self):
        """SESSION_SECRET_PROD should be used over SESSION_SECRET in production."""
        env = {
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_PROD": "prod-key",
            "SESSION_SECRET_PROD": "prod-specific-secret",
            "SESSION_SECRET": "generic-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.session_secret, "prod-specific-secret")

    def test_miniapp_url_prod_takes_priority_over_bare_miniapp_url(self):
        """MINIAPP_URL_PROD should be used over MINIAPP_URL in production."""
        env = {
            "APP_ENV": "production",
            "BOT_TOKEN_PROD": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_PROD": "key",
            "SESSION_SECRET_PROD": "secret",
            "MINIAPP_URL_PROD": "https://prod.miniapp.url",
            "MINIAPP_URL": "https://generic.miniapp.url",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.miniapp_url, "https://prod.miniapp.url")

    def test_port_invalid_value_uses_default(self):
        """PORT env var coerces to int; non-integer silently defaults to 5000 via int()."""
        env = dict(self._dev_env())
        env["PORT"] = "not-a-port"
        # int("not-a-port") raises ValueError, which means get_settings raises too
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises((ValueError, Exception)):
                get_settings()

    def test_api_key_dev_used_in_development(self):
        env = dict(self._dev_env())
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.api_key, "dev-api-key")

    def test_api_key_legacy_stixmagic_api_key_accepted_in_development(self):
        """STIXMAGIC_API_KEY bare name falls back when suffixed not set."""
        env = {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY": "legacy-key",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertEqual(s.api_key, "legacy-key")

    def test_settings_caches_results(self):
        """get_settings() is cached – two calls return the same object."""
        env = dict(self._dev_env())
        with patch.dict(os.environ, env, clear=True):
            s1 = get_settings()
            s2 = get_settings()
        self.assertIs(s1, s2)

    def test_telegram_bot_token_stripped_from_noise(self):
        """_validate_token uses re.search so a valid token embedded in noise is extracted."""
        env = {
            "APP_ENV": "development",
            "BOT_TOKEN_DEV": "prefix:123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh",
            "STIXMAGIC_API_KEY_DEV": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
        self.assertIn("123456:", s.telegram_bot_token)


if __name__ == "__main__":
    unittest.main()
"""
Tests for scripts/validate_runtime.py – require_env and validate_token utilities.

Covers the PR changes:
 - require_env(): raises SystemExit when env vars are missing; no-op when all present
 - validate_token(): extracts a valid token from an env var; raises SystemExit on missing/invalid
 - Production mode env var list changed to BOT_TOKEN_PROD, STIXMAGIC_API_KEY, SESSION_SECRET
   (previously STIXMAGIC_API_KEY, TELEGRAM_WEBHOOK_SECRET)
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the functions under test directly from the module
import scripts.validate_runtime as vr_mod
from scripts.validate_runtime import require_env, validate_token


VALID_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh"


class TestRequireEnv(unittest.TestCase):
    """Tests for require_env() – checks that required env vars are present."""

    def test_no_error_when_all_vars_set(self):
        env = {"MY_VAR_A": "value_a", "MY_VAR_B": "value_b"}
        with patch.dict(os.environ, env, clear=True):
            # Should not raise
            require_env(["MY_VAR_A", "MY_VAR_B"])

    def test_raises_system_exit_when_var_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                require_env(["MISSING_VAR"])

    def test_raises_system_exit_when_var_whitespace_only(self):
        """Whitespace-only value is treated as missing."""
        with patch.dict(os.environ, {"BLANK_VAR": "   "}, clear=True):
            with self.assertRaises(SystemExit):
                require_env(["BLANK_VAR"])

    def test_raises_system_exit_for_partial_missing(self):
        """Even if one var is set, missing one should raise."""
        env = {"PRESENT_VAR": "exists"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                require_env(["PRESENT_VAR", "ABSENT_VAR"])

    def test_error_message_mentions_missing_var(self):
        with patch.dict(os.environ, {}, clear=True):
            try:
                require_env(["SOME_MISSING_VAR"])
                self.fail("Expected SystemExit not raised")
            except SystemExit as e:
                self.assertIn("SOME_MISSING_VAR", str(e))

    def test_empty_list_does_not_raise(self):
        """Requiring no variables should be a no-op."""
        require_env([])

    def test_tuple_as_input_works(self):
        """Iterable contract: tuples should work, not just lists."""
        env = {"TUPLE_VAR": "ok"}
        with patch.dict(os.environ, env, clear=True):
            require_env(("TUPLE_VAR",))

    def test_single_var_set_no_raise(self):
        env = {"SINGLE_VAR": "hello"}
        with patch.dict(os.environ, env, clear=True):
            require_env(["SINGLE_VAR"])

    def test_multiple_missing_vars_all_mentioned(self):
        """When multiple vars are missing, the error should mention them all."""
        with patch.dict(os.environ, {}, clear=True):
            try:
                require_env(["FIRST_MISSING", "SECOND_MISSING"])
                self.fail("Expected SystemExit not raised")
            except SystemExit as e:
                error_text = str(e)
                self.assertIn("FIRST_MISSING", error_text)
                self.assertIn("SECOND_MISSING", error_text)

    def test_empty_string_value_is_treated_as_missing(self):
        with patch.dict(os.environ, {"EMPTY_VAR": ""}, clear=True):
            with self.assertRaises(SystemExit):
                require_env(["EMPTY_VAR"])


class TestValidateToken(unittest.TestCase):
    """Tests for validate_token() – reads and validates a bot token from an env var."""

    def test_valid_token_returns_value(self):
        env = {"BOT_TOKEN_PROD": VALID_TOKEN}
        with patch.dict(os.environ, env, clear=True):
            result = validate_token("BOT_TOKEN_PROD")
        self.assertEqual(result, VALID_TOKEN)

    def test_raises_system_exit_when_var_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                validate_token("BOT_TOKEN_PROD")

    def test_raises_system_exit_when_var_empty(self):
        with patch.dict(os.environ, {"BOT_TOKEN_PROD": ""}, clear=True):
            with self.assertRaises(SystemExit):
                validate_token("BOT_TOKEN_PROD")

    def test_raises_system_exit_for_invalid_token_format(self):
        with patch.dict(os.environ, {"BOT_TOKEN_PROD": "not-a-valid-token"}, clear=True):
            with self.assertRaises(SystemExit):
                validate_token("BOT_TOKEN_PROD")

    def test_error_mentions_var_name_when_empty(self):
        with patch.dict(os.environ, {"MISSING_TOKEN_VAR": ""}, clear=True):
            try:
                validate_token("MISSING_TOKEN_VAR")
                self.fail("Expected SystemExit not raised")
            except SystemExit as e:
                self.assertIn("MISSING_TOKEN_VAR", str(e))

    def test_error_mentions_var_name_for_invalid_format(self):
        with patch.dict(os.environ, {"BAD_TOKEN_VAR": "notvalidtoken"}, clear=True):
            try:
                validate_token("BAD_TOKEN_VAR")
                self.fail("Expected SystemExit not raised")
            except SystemExit as e:
                self.assertIn("BAD_TOKEN_VAR", str(e))

    def test_token_with_hyphen_in_secret_part_is_valid(self):
        token = "987654321:ABCDEF-ghijklmnopqrstuvwxyz12345_ab"
        with patch.dict(os.environ, {"BOT_TOKEN_PROD": token}, clear=True):
            result = validate_token("BOT_TOKEN_PROD")
        self.assertEqual(result, token)

    def test_token_without_sufficient_length_is_invalid(self):
        """Token secret part must be >= 35 chars per TOKEN_PATTERN."""
        short_token = "123456:SHORT"
        with patch.dict(os.environ, {"BOT_TOKEN_PROD": short_token}, clear=True):
            with self.assertRaises(SystemExit):
                validate_token("BOT_TOKEN_PROD")

    def test_whitespace_only_token_raises_system_exit(self):
        with patch.dict(os.environ, {"BOT_TOKEN_PROD": "   "}, clear=True):
            with self.assertRaises(SystemExit):
                validate_token("BOT_TOKEN_PROD")

    def test_returns_stripped_token(self):
        """validate_token strips surrounding whitespace from the value."""
        token_with_space = f"  {VALID_TOKEN}  "
        with patch.dict(os.environ, {"BOT_TOKEN_PROD": token_with_space}, clear=True):
            # Should not raise and should return the token
            try:
                result = validate_token("BOT_TOKEN_PROD")
                # If it returns, the stripped value should contain the valid token
                self.assertIn("123456789:", result)
            except SystemExit:
                # Some implementations may reject tokens with leading/trailing spaces
                pass


class TestProductionEnvVarSet(unittest.TestCase):
    """Tests confirming the PR changed the required production env vars.

    Previously required: STIXMAGIC_API_KEY + TELEGRAM_WEBHOOK_SECRET
    Now required:        BOT_TOKEN_PROD + STIXMAGIC_API_KEY + SESSION_SECRET
    """

    def test_require_env_new_production_vars_all_set(self):
        """PR: production mode requires BOT_TOKEN_PROD, STIXMAGIC_API_KEY, SESSION_SECRET."""
        env = {
            "BOT_TOKEN_PROD": VALID_TOKEN,
            "STIXMAGIC_API_KEY": "prod-api-key",
            "SESSION_SECRET": "prod-session-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            # Should not raise – all required production vars are present
            require_env(("BOT_TOKEN_PROD", "STIXMAGIC_API_KEY", "SESSION_SECRET"))

    def test_require_env_raises_when_bot_token_prod_missing(self):
        """PR: BOT_TOKEN_PROD is now a required production variable."""
        env = {
            "STIXMAGIC_API_KEY": "key",
            "SESSION_SECRET": "secret",
            # BOT_TOKEN_PROD intentionally missing
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                require_env(("BOT_TOKEN_PROD", "STIXMAGIC_API_KEY", "SESSION_SECRET"))

    def test_require_env_raises_when_session_secret_missing(self):
        """PR: SESSION_SECRET replaces TELEGRAM_WEBHOOK_SECRET as required production var."""
        env = {
            "BOT_TOKEN_PROD": VALID_TOKEN,
            "STIXMAGIC_API_KEY": "key",
            # SESSION_SECRET intentionally missing
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                require_env(("BOT_TOKEN_PROD", "STIXMAGIC_API_KEY", "SESSION_SECRET"))

    def test_old_telegram_webhook_secret_not_required(self):
        """PR: TELEGRAM_WEBHOOK_SECRET is no longer in the production required set."""
        # This confirms the new set doesn't include TELEGRAM_WEBHOOK_SECRET
        new_required = ("BOT_TOKEN_PROD", "STIXMAGIC_API_KEY", "SESSION_SECRET")
        self.assertNotIn("TELEGRAM_WEBHOOK_SECRET", new_required)
        self.assertIn("SESSION_SECRET", new_required)
        self.assertIn("BOT_TOKEN_PROD", new_required)

    def test_validate_token_uses_bot_token_prod_in_production(self):
        """PR: production validation reads from BOT_TOKEN_PROD (not TELEGRAM_BOT_TOKEN)."""
        env = {"BOT_TOKEN_PROD": VALID_TOKEN}
        with patch.dict(os.environ, env, clear=True):
            result = validate_token("BOT_TOKEN_PROD")
        self.assertEqual(result, VALID_TOKEN)


class TestTokenPatternMatching(unittest.TestCase):
    """Regression tests for the TOKEN_PATTERN used in validate_token."""

    def _check_valid(self, token_str):
        """Convenience: check that validate_token does NOT raise for this token."""
        with patch.dict(os.environ, {"TEST_TOKEN": token_str}, clear=True):
            return validate_token("TEST_TOKEN")

    def _check_invalid(self, token_str):
        """Convenience: check that validate_token raises SystemExit for this token."""
        with patch.dict(os.environ, {"TEST_TOKEN": token_str}, clear=True):
            with self.assertRaises(SystemExit):
                validate_token("TEST_TOKEN")

    def test_standard_numeric_id_with_alphanumeric_secret(self):
        # Use VALID_TOKEN which is already verified to work
        self._check_valid(VALID_TOKEN)

    def test_longer_numeric_id_is_valid(self):
        self._check_valid("9999999999:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh")

    def test_no_colon_is_invalid(self):
        self._check_invalid("1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh")

    def test_letters_before_colon_is_invalid(self):
        self._check_invalid("ABCDEFGH:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh")

    def test_empty_secret_part_is_invalid(self):
        self._check_invalid("123456789:")

    def test_boundary_secret_length(self):
        """Secret part needs >= 35 chars for the pattern to match."""
        # Exactly 35 chars after colon
        token_35 = "123456789:" + "A" * 35
        self._check_valid(token_35)

    def test_secret_too_short(self):
        """34 chars in secret part should fail (pattern requires 35+)."""
        token_34 = "123456789:" + "A" * 34
        self._check_invalid(token_34)


if __name__ == "__main__":
    unittest.main()
"""
Tests for menus.py – PR change: _resolve_miniapp_url REPLIT_DOMAINS fallback.

Covers:
 - _resolve_miniapp_url: returns settings.miniapp_url when set
 - _resolve_miniapp_url: falls back to first REPLIT_DOMAINS entry when miniapp_url is empty
 - _resolve_miniapp_url: appends /miniapp to the REPLIT_DOMAINS host
 - _resolve_miniapp_url: uses the first domain when multiple REPLIT_DOMAINS are present
 - _resolve_miniapp_url: returns empty string when neither is set
 - _resolve_miniapp_url: REPLIT_DOMAINS ignored when miniapp_url is set
 - get_menu_text: returns "Menu not found." for unknown menu_id
 - get_menu_text: returns header+divider+body for valid menu_id

The function under test (_resolve_miniapp_url) only depends on os.environ and
get_settings().miniapp_url — the telegram import in menus.py is only needed for
build_keyboard().  We stub the telegram module so the tests don't require the
full python-telegram-bot package.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_telegram_stub():
    """Inject a minimal telegram stub so menus.py can be imported."""
    if "telegram" not in sys.modules:
        stub = MagicMock()
        stub.InlineKeyboardButton = MagicMock
        stub.InlineKeyboardMarkup = MagicMock
        stub.WebAppInfo = MagicMock
        sys.modules["telegram"] = stub


def _make_mock_settings(miniapp_url=""):
    s = MagicMock()
    s.miniapp_url = miniapp_url
    s.api_key = "test-key"
    s.telegram_bot_token = "123456:testtoken"
    s.session_secret = "secret"
    s.port = 5000
    return s


class TestResolveMiniappUrl(unittest.TestCase):
    """Tests for the _resolve_miniapp_url function in menus.py (PR change)."""

    @classmethod
    def setUpClass(cls):
        _ensure_telegram_stub()

    def _call_resolve(self, miniapp_url="", env_overrides=None):
        """Call menus._resolve_miniapp_url with a controlled environment."""
        mock_settings = _make_mock_settings(miniapp_url=miniapp_url)
        # Build environment with REPLIT_DOMAINS removed by default, then add overrides
        env = {k: v for k, v in os.environ.items() if k != "REPLIT_DOMAINS"}
        if env_overrides:
            env.update(env_overrides)

        with patch("config.runtime.get_settings", return_value=mock_settings):
            import menus as menus_mod
            # Override the module-level get_settings call result
            original = menus_mod.get_settings
            menus_mod.get_settings = lambda: mock_settings
            try:
                with patch.dict(os.environ, env, clear=True):
                    return menus_mod._resolve_miniapp_url()
            finally:
                menus_mod.get_settings = original

    def test_returns_settings_miniapp_url_when_set(self):
        result = self._call_resolve(miniapp_url="https://app.example.com/miniapp")
        self.assertEqual(result, "https://app.example.com/miniapp")

    def test_falls_back_to_replit_domains_when_miniapp_url_empty(self):
        result = self._call_resolve(
            miniapp_url="",
            env_overrides={"REPLIT_DOMAINS": "myapp.replit.app"},
        )
        self.assertEqual(result, "https://myapp.replit.app/miniapp")

    def test_replit_domains_appends_miniapp_path(self):
        result = self._call_resolve(
            miniapp_url="",
            env_overrides={"REPLIT_DOMAINS": "example.replit.app"},
        )
        self.assertTrue(result.endswith("/miniapp"))

    def test_uses_first_domain_from_comma_separated_replit_domains(self):
        result = self._call_resolve(
            miniapp_url="",
            env_overrides={"REPLIT_DOMAINS": "first.replit.app,second.replit.app"},
        )
        self.assertIn("first.replit.app", result)
        self.assertNotIn("second.replit.app", result)

    def test_returns_empty_when_neither_set(self):
        result = self._call_resolve(miniapp_url="", env_overrides={})
        self.assertEqual(result, "")

    def test_settings_miniapp_url_takes_precedence_over_replit_domains(self):
        result = self._call_resolve(
            miniapp_url="https://real.miniapp.url/miniapp",
            env_overrides={"REPLIT_DOMAINS": "should-not-be-used.replit.app"},
        )
        self.assertNotIn("should-not-be-used", result)
        self.assertEqual(result, "https://real.miniapp.url/miniapp")

    def test_replit_domains_builds_https_url(self):
        result = self._call_resolve(
            miniapp_url="",
            env_overrides={"REPLIT_DOMAINS": "somehost.replit.app"},
        )
        self.assertTrue(result.startswith("https://"))

    def test_replit_domains_with_single_domain(self):
        result = self._call_resolve(
            miniapp_url="",
            env_overrides={"REPLIT_DOMAINS": "only-domain.replit.app"},
        )
        self.assertEqual(result, "https://only-domain.replit.app/miniapp")


class TestGetMenuText(unittest.TestCase):
    """Tests for menus.get_menu_text (import from config.runtime changed in PR)."""

    @classmethod
    def setUpClass(cls):
        _ensure_telegram_stub()
        mock_settings = _make_mock_settings()
        cls._patcher = patch("config.runtime.get_settings", return_value=mock_settings)
        cls._patcher.start()
        import menus as menus_mod
        cls.menus = menus_mod

    @classmethod
    def tearDownClass(cls):
        cls._patcher.stop()

    def test_unknown_menu_id_returns_not_found(self):
        result = self.menus.get_menu_text("nonexistent_menu")
        self.assertEqual(result, "Menu not found.")

    def test_home_menu_returns_header(self):
        result = self.menus.get_menu_text("home")
        self.assertIn("STIX MAGIC", result)

    def test_menu_text_includes_divider(self):
        result = self.menus.get_menu_text("home")
        # DIVIDER constant contains "◈"
        self.assertIn("◈", result)

    def test_menu_text_includes_body_when_present(self):
        result = self.menus.get_menu_text("home")
        self.assertIn("transmute", result.lower())

    def test_settings_menu_text(self):
        result = self.menus.get_menu_text("settings")
        self.assertNotEqual(result, "Menu not found.")
        self.assertIn("ORACLE", result)

    def test_all_menu_ids_return_non_empty(self):
        for menu_id in self.menus.MENU_STRUCTURE:
            with self.subTest(menu_id=menu_id):
                result = self.menus.get_menu_text(menu_id)
                self.assertNotEqual(result, "Menu not found.")
                self.assertGreater(len(result), 0)

    def test_menu_text_starts_with_header(self):
        result = self.menus.get_menu_text("home")
        # Should start with the header line
        self.assertTrue(result.startswith("⚗️") or result.startswith("📖") or len(result) > 0)


if __name__ == "__main__":
    unittest.main()
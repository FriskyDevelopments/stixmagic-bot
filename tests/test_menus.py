"""
Tests for menus.py – menu building and REPLIT_DOMAINS fallback.

Covers the PR changes:
 - _resolve_miniapp_url: uses get_settings().miniapp_url when set
 - _resolve_miniapp_url: falls back to REPLIT_DOMAINS when miniapp_url is empty
 - _resolve_miniapp_url: returns empty/None when neither is set
 - get_menu_text: returns header + divider + body (docstring removed, logic unchanged)
 - build_keyboard: returns InlineKeyboardMarkup for known menu IDs

Note: menus.py calls get_settings() at import time to populate MINIAPP_URL.
We stub config.runtime.get_settings before the import so menus can load.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub_telegram():
    """Inject telegram stubs so menus.py can be imported in tests."""
    if "telegram" not in sys.modules:
        tg = MagicMock()
        tg.__name__ = "telegram"
        sys.modules["telegram"] = tg
        sys.modules["telegram.ext"] = MagicMock()


_stub_telegram()


def _make_settings(miniapp_url: str = "") -> MagicMock:
    s = MagicMock()
    s.miniapp_url = miniapp_url
    s.api_key = "key"
    s.telegram_bot_token = "123:token"
    s.session_secret = ""
    s.port = 5000
    return s


# Ensure menus can be imported by stubbing out get_settings at module level.
# menus.py does `from config.runtime import get_settings` then calls it
# immediately, so we need the stub in place before the first import.
_default_stub_settings = _make_settings(miniapp_url="")
_menus_patch = patch("config.runtime.get_settings", return_value=_default_stub_settings)
_menus_patch.start()

import menus as _menus_module  # noqa: E402 – must come after the patch

_menus_patch.stop()


class TestResolveMiniappUrl(unittest.TestCase):
    """Tests for menus._resolve_miniapp_url() – the PR change.

    menus.py uses ``from config.runtime import get_settings``, so the name
    bound in the menus module is ``menus.get_settings``.  We patch that
    name directly via ``patch.object(menus_module, "get_settings", ...)``
    to intercept calls made *inside* the module function.
    """

    def _call_resolve(self, miniapp_url: str = "", replit_domains: str = "") -> str:
        settings = _make_settings(miniapp_url=miniapp_url)
        env = {"REPLIT_DOMAINS": replit_domains} if replit_domains else {}
        with patch.object(_menus_module, "get_settings", return_value=settings):
            with patch.dict(os.environ, env, clear=False):
                if not replit_domains:
                    os.environ.pop("REPLIT_DOMAINS", None)
                result = _menus_module._resolve_miniapp_url()
        return result or ""

    def test_returns_settings_miniapp_url_when_set(self):
        result = self._call_resolve(miniapp_url="https://example.com/miniapp")
        self.assertEqual(result, "https://example.com/miniapp")

    def test_falls_back_to_replit_domains_when_miniapp_url_empty(self):
        result = self._call_resolve(miniapp_url="", replit_domains="myapp.replit.app")
        self.assertEqual(result, "https://myapp.replit.app/miniapp")

    def test_uses_first_domain_from_comma_separated_list(self):
        result = self._call_resolve(
            miniapp_url="",
            replit_domains="first.replit.app,second.replit.app,third.replit.app",
        )
        self.assertEqual(result, "https://first.replit.app/miniapp")

    def test_returns_falsy_when_neither_set(self):
        result = self._call_resolve(miniapp_url="", replit_domains="")
        self.assertFalse(result)

    def test_settings_url_takes_priority_over_replit_domains(self):
        """When settings.miniapp_url is set, REPLIT_DOMAINS should not be used."""
        result = self._call_resolve(
            miniapp_url="https://explicit.example.com/app",
            replit_domains="replit.example.app",
        )
        self.assertEqual(result, "https://explicit.example.com/app")

    def test_replit_url_has_correct_scheme(self):
        result = self._call_resolve(miniapp_url="", replit_domains="app.replit.app")
        self.assertTrue(result.startswith("https://"))

    def test_replit_url_ends_with_miniapp_path(self):
        result = self._call_resolve(miniapp_url="", replit_domains="app.replit.app")
        self.assertTrue(result.endswith("/miniapp"))

    def test_single_domain_no_comma(self):
        result = self._call_resolve(miniapp_url="", replit_domains="solo.replit.app")
        self.assertEqual(result, "https://solo.replit.app/miniapp")


class TestGetMenuText(unittest.TestCase):
    """get_menu_text – logic unchanged by PR (docstring removed only)."""

    def test_known_menu_id_returns_text(self):
        result = _menus_module.get_menu_text("home")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_unknown_menu_id_returns_not_found(self):
        result = _menus_module.get_menu_text("nonexistent_menu_xyz")
        self.assertEqual(result, "Menu not found.")

    def test_text_includes_header(self):
        result = _menus_module.get_menu_text("home")
        self.assertIn("STIX MAGIC", result)

    def test_text_includes_divider(self):
        result = _menus_module.get_menu_text("home")
        self.assertIn(_menus_module.DIVIDER, result)

    def test_settings_menu_text(self):
        result = _menus_module.get_menu_text("settings")
        self.assertIn("ORACLE", result)

    def test_help_menu_text(self):
        result = _menus_module.get_menu_text("help")
        self.assertIn("CODEX", result)

    def test_menu_with_body_includes_body(self):
        result = _menus_module.get_menu_text("home")
        self.assertIn("sticker", result.lower())


class TestBuildKeyboard(unittest.TestCase):
    """build_keyboard – smoke tests verifying structure."""

    def test_known_menu_returns_keyboard(self):
        result = _menus_module.build_keyboard("home")
        self.assertIsNotNone(result)

    def test_unknown_menu_returns_empty_keyboard(self):
        result = _menus_module.build_keyboard("no_such_menu")
        self.assertIsNotNone(result)

    def test_all_defined_menus_build_without_error(self):
        for menu_id in _menus_module.MENU_STRUCTURE:
            with self.subTest(menu_id=menu_id):
                result = _menus_module.build_keyboard(menu_id)
                self.assertIsNotNone(result)

    def test_menu_structure_contains_expected_menus(self):
        expected = {"home", "my_packs", "settings", "help", "catalog"}
        actual = set(_menus_module.MENU_STRUCTURE.keys())
        self.assertTrue(expected.issubset(actual))


if __name__ == "__main__":
    unittest.main()
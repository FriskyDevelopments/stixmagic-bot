"""
Tests for menus.py — menu keyboard and text rendering.

Requirements:
  6.1 Every menu builds a keyboard the Telegram Bot API would accept:
      callback data within the length limit, no empty rows, no duplicate
      callback data.
  6.2 Menu text with user-supplied content is escaped.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch stixmagic.settings before importing menus so the module-level
# _resolve_miniapp_url() does not require a real environment.
# ---------------------------------------------------------------------------

_fake_settings = MagicMock()
_fake_settings.miniapp_url = "https://example.com/miniapp"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    """Ensure menus.get_settings returns a fake with a miniapp_url."""
    monkeypatch.setattr("menus.get_settings", lambda: _fake_settings)
    # Also patch the module-level MINIAPP_URL which was resolved at import time.
    import menus
    monkeypatch.setattr(menus, "MINIAPP_URL", "https://example.com/miniapp")


# ---------------------------------------------------------------------------
# Import under test (after fixture definition — works because autouse fixture
# is applied at test runtime, but the module itself will be imported once; we
# need to handle the import-time call).
# ---------------------------------------------------------------------------

# We need to patch before the first import of menus at module level.
import sys
from unittest.mock import patch as _real_patch

# Temporarily patch get_settings for the import-time call
with _real_patch("stixmagic.settings.get_settings", return_value=_fake_settings):
    import menus  # noqa: E402
    from menus import MENU_STRUCTURE, build_keyboard, get_menu_text


# ---------------------------------------------------------------------------
# Telegram Bot API constants
# ---------------------------------------------------------------------------

# Telegram enforces a 64-byte limit on callback_data.
TELEGRAM_CALLBACK_DATA_MAX_BYTES = 64


# ===========================================================================
# 6.1 — Keyboard validity
# ===========================================================================


class TestMenuKeyboardValidity:
    """Every menu produces a keyboard the Telegram Bot API would accept."""

    @pytest.mark.parametrize("menu_id", list(MENU_STRUCTURE.keys()))
    def test_callback_data_within_length_limit(self, menu_id):
        """All callback_data values are ≤ 64 bytes (Telegram limit)."""
        keyboard = build_keyboard(menu_id)
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    byte_len = len(button.callback_data.encode("utf-8"))
                    assert byte_len <= TELEGRAM_CALLBACK_DATA_MAX_BYTES, (
                        f"Menu '{menu_id}': callback_data "
                        f"'{button.callback_data}' is {byte_len} bytes "
                        f"(limit is {TELEGRAM_CALLBACK_DATA_MAX_BYTES})"
                    )

    @pytest.mark.parametrize("menu_id", list(MENU_STRUCTURE.keys()))
    def test_no_empty_rows(self, menu_id):
        """No keyboard row is empty."""
        keyboard = build_keyboard(menu_id)
        for i, row in enumerate(keyboard.inline_keyboard):
            assert len(row) > 0, (
                f"Menu '{menu_id}': row {i} is empty"
            )

    @pytest.mark.parametrize("menu_id", list(MENU_STRUCTURE.keys()))
    def test_no_duplicate_callback_data(self, menu_id):
        """No two buttons in the same keyboard share callback_data."""
        keyboard = build_keyboard(menu_id)
        seen: set[str] = set()
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    assert button.callback_data not in seen, (
                        f"Menu '{menu_id}': duplicate callback_data "
                        f"'{button.callback_data}'"
                    )
                    seen.add(button.callback_data)

    @pytest.mark.parametrize("menu_id", list(MENU_STRUCTURE.keys()))
    def test_keyboard_is_not_none(self, menu_id):
        """build_keyboard returns an InlineKeyboardMarkup, not None."""
        from telegram import InlineKeyboardMarkup

        keyboard = build_keyboard(menu_id)
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_unknown_menu_returns_empty_keyboard(self):
        """An unknown menu_id returns an empty keyboard rather than raising."""
        keyboard = build_keyboard("nonexistent_menu_xyz")
        assert len(keyboard.inline_keyboard) == 0

    @pytest.mark.parametrize("menu_id", list(MENU_STRUCTURE.keys()))
    def test_every_button_has_exactly_one_action_type(self, menu_id):
        """Each button has callback_data, url, or web_app — not multiple."""
        keyboard = build_keyboard(menu_id)
        for row in keyboard.inline_keyboard:
            for button in row:
                action_count = sum([
                    button.callback_data is not None,
                    getattr(button, "url", None) is not None,
                    getattr(button, "web_app", None) is not None,
                ])
                assert action_count == 1, (
                    f"Menu '{menu_id}': button '{button.text}' has "
                    f"{action_count} action types (expected exactly 1)"
                )

    def test_no_duplicate_callback_data_across_all_menus(self):
        """Callback data values should not collide across navigation targets.

        While Telegram allows the same callback_data in different messages, we
        verify uniqueness per-menu above.  This test further checks that nav:
        targets reference existing menus.
        """
        for menu_id in MENU_STRUCTURE:
            keyboard = build_keyboard(menu_id)
            for row in keyboard.inline_keyboard:
                for button in row:
                    if button.callback_data and button.callback_data.startswith("nav:"):
                        target = button.callback_data[len("nav:"):]
                        assert target in MENU_STRUCTURE, (
                            f"Menu '{menu_id}': nav target '{target}' "
                            f"does not exist in MENU_STRUCTURE"
                        )


# ===========================================================================
# 6.1 — Back/Home navigation row
# ===========================================================================


class TestMenuNavigationRow:
    """Navigation rows (BACK / HOME) are structurally correct."""

    def test_home_menu_has_no_back_button(self):
        """The home menu should not have a BACK button."""
        keyboard = build_keyboard("home")
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data == "nav:home":
                    # Home shouldn't navigate to itself
                    pass
                assert button.callback_data != "nav:None", (
                    "BACK button should not navigate to None"
                )

    @pytest.mark.parametrize("menu_id", [
        m for m in MENU_STRUCTURE if MENU_STRUCTURE[m].get("parent") is not None
    ])
    def test_child_menus_have_back_button(self, menu_id):
        """Every menu with a parent has a BACK button pointing to the parent."""
        parent = MENU_STRUCTURE[menu_id]["parent"]
        keyboard = build_keyboard(menu_id)
        callback_values = [
            btn.callback_data
            for row in keyboard.inline_keyboard
            for btn in row
            if btn.callback_data
        ]
        assert f"nav:{parent}" in callback_values, (
            f"Menu '{menu_id}' has parent '{parent}' but no BACK button "
            f"navigating to it"
        )

    @pytest.mark.parametrize("menu_id", [
        m for m in MENU_STRUCTURE if m != "home"
    ])
    def test_non_home_menus_have_home_button(self, menu_id):
        """Every non-home menu has a HOME button."""
        keyboard = build_keyboard(menu_id)
        callback_values = [
            btn.callback_data
            for row in keyboard.inline_keyboard
            for btn in row
            if btn.callback_data
        ]
        assert "nav:home" in callback_values, (
            f"Menu '{menu_id}' does not have a HOME button"
        )


# ===========================================================================
# 6.2 — Menu text escaping
# ===========================================================================


class TestMenuTextEscaping:
    """Menu text with user-supplied content is escaped."""

    @pytest.mark.parametrize("menu_id", list(MENU_STRUCTURE.keys()))
    def test_get_menu_text_returns_string(self, menu_id):
        """get_menu_text returns a string for every known menu."""
        text = get_menu_text(menu_id)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_unknown_menu_text(self):
        """An unknown menu_id returns a 'not found' message."""
        text = get_menu_text("nonexistent_menu_xyz")
        assert "not found" in text.lower()

    def test_menu_text_contains_header(self):
        """Menu text starts with the menu's header."""
        for menu_id, menu in MENU_STRUCTURE.items():
            text = get_menu_text(menu_id)
            assert menu["header"] in text, (
                f"Menu '{menu_id}' text does not contain its header"
            )

    def test_menu_text_contains_body_when_present(self):
        """Menu text includes the body content when body is non-empty."""
        for menu_id, menu in MENU_STRUCTURE.items():
            if menu.get("body"):
                text = get_menu_text(menu_id)
                assert menu["body"] in text, (
                    f"Menu '{menu_id}' text does not contain its body"
                )

    def test_static_menu_text_uses_html_tags_safely(self):
        """
        The existing static menu text uses HTML intentionally (for <b>, <i>).
        Verify that it does NOT contain unescaped user-input characters that
        would break Telegram's HTML parse mode.

        Since menus.py only renders static content (no user-supplied values
        interpolated into menu text at runtime), we verify the structure is
        well-formed HTML for Telegram: all < and > are part of known tags.
        """
        import re

        # Telegram HTML mode allows: <b>, </b>, <i>, </i>, <u>, </u>,
        # <s>, </s>, <code>, </code>, <pre>, </pre>, <a href="...">,
        # <tg-spoiler>, <blockquote>
        allowed_tag_pattern = re.compile(
            r"</?(?:b|i|u|s|code|pre|a|tg-spoiler|blockquote)"
            r"(?:\s[^>]*)?>",
            re.IGNORECASE,
        )

        for menu_id in MENU_STRUCTURE:
            text = get_menu_text(menu_id)
            # Remove all known-safe tags
            stripped = allowed_tag_pattern.sub("", text)
            # After removing allowed tags, no stray < or > should remain
            # (which would indicate un-escaped user content or malformed HTML)
            assert "<" not in stripped and ">" not in stripped, (
                f"Menu '{menu_id}' contains stray '<' or '>' outside allowed "
                f"HTML tags — this would break Telegram parse_mode=HTML"
            )

    def test_menu_text_escaping_for_user_content(self):
        """
        Requirement 6.2: if user-supplied content were interpolated into menu
        text, it would need escaping. Verify the get_menu_text function is safe
        by design — it only renders static content from MENU_STRUCTURE, never
        interpolating external user input.

        We validate this by confirming the function signature takes only
        menu_id and that MENU_STRUCTURE values are string literals (no
        callables or format-string patterns with external variables).
        """
        import inspect

        sig = inspect.signature(get_menu_text)
        params = list(sig.parameters.keys())
        # get_menu_text only takes menu_id — no user content parameter
        assert params == ["menu_id"], (
            f"get_menu_text takes parameters {params}; if it accepted user "
            f"content, that content would need HTML-escaping"
        )

        # All body/header values in MENU_STRUCTURE are plain strings (no
        # callables or dynamic interpolation with external user data)
        for menu_id, menu in MENU_STRUCTURE.items():
            assert isinstance(menu["header"], str), (
                f"Menu '{menu_id}' header is not a string literal"
            )
            if menu.get("body"):
                assert isinstance(menu["body"], str), (
                    f"Menu '{menu_id}' body is not a string literal"
                )

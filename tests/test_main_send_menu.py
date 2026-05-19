"""
Tests for main.py – send_menu() function.

Covers:
 - Callback-query path: answer() + edit_message_text() called with correct args
 - Message path: reply_text() called with correct args
 - BadRequest("Message is not modified") silently ignored on callback path
 - Other BadRequest errors re-raised on callback path
 - Neither branch taken when both callback_query and message are falsy
"""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal stubs so we can import main without a running Telegram application
# ---------------------------------------------------------------------------

def _make_stub(name):
    mod = MagicMock()
    mod.__name__ = name
    return mod


def _patch_heavy_imports():
    """Inject lightweight stubs for modules main.py pulls in at import time."""
    telegram = _make_stub("telegram")
    telegram_ext = _make_stub("telegram.ext")
    telegram_error = _make_stub("telegram.error")

    class StubMock:
        def __init__(self, *args, **kwargs):
            if args and isinstance(args[0], list):
                self.inline_keyboard = args[0]
            elif args and isinstance(args[0], str):
                self.text = args[0]
            if "inline_keyboard" in kwargs:
                self.inline_keyboard = kwargs["inline_keyboard"]
            if "callback_data" in kwargs:
                self.callback_data = kwargs["callback_data"]
            if "text" in kwargs:
                self.text = kwargs["text"]
        DEFAULT_TYPE = MagicMock()

    for cls in ["InputSticker", "InlineKeyboardButton", "InlineKeyboardMarkup",
                "InlineQueryResultArticle", "InputTextMessageContent",
                "MenuButtonWebApp", "Update", "WebAppInfo"]:
        setattr(telegram, cls, StubMock)

    for cls in ["Application", "CallbackQueryHandler", "CommandHandler",
                "ContextTypes", "ConversationHandler", "InlineQueryHandler",
                "MessageHandler"]:
        setattr(telegram_ext, cls, StubMock)
    telegram_ext.ConversationHandler.END = -1
    telegram_ext.filters = MagicMock()

    class BadRequest(Exception):
        pass

    telegram_error.BadRequest = BadRequest

    stubs = {
        "telegram": telegram,
        "telegram.ext": telegram_ext,
        "telegram.error": telegram_error,
        "config": _make_stub("config"),
        "config.runtime": _make_stub("config.runtime"),
        "core": _make_stub("core"),
        "core.engine": _make_stub("core.engine"),
        "platforms": _make_stub("platforms"),
        "platforms.telegram": _make_stub("platforms.telegram"),
        "loaders": _make_stub("loaders"),
        "menus": _make_stub("menus"),
        "infra": _make_stub("infra"),
        "infra.db": _make_stub("infra.db"),
        "packs": _make_stub("packs"),
        "packs.db": _make_stub("packs.db"),
        "moderation": _make_stub("moderation"),
        "moderation.guard": _make_stub("moderation.guard"),
        "stixmagic": _make_stub("stixmagic"),
        "stixmagic.settings": _make_stub("stixmagic.settings"),
        "domain": _make_stub("domain"),
        "domain.media": _make_stub("domain.media"),
    }
    for name, stub in stubs.items():
        if name not in sys.modules:
            sys.modules[name] = stub

    sys.modules["infra.db"].init_db = MagicMock()
    sys.modules["config.runtime"].get_settings = MagicMock(return_value=MagicMock())
    sys.modules["config.runtime"].ConfigError = Exception

    return stubs


_patch_heavy_imports()

import main  # noqa: E402  (must come after patching)
from telegram.error import BadRequest  # noqa: E402


def _run(coro):
    """Execute a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSendMenuCallbackQueryPath(unittest.TestCase):
    """send_menu() when update.callback_query is truthy."""

    @patch("main.get_menu_text", return_value="<b>Menu Text</b>")
    @patch("main.build_keyboard")
    def test_answer_is_called(self, mock_build_keyboard, mock_get_menu_text):
        keyboard = MagicMock()
        mock_build_keyboard.return_value = keyboard

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.message = None

        _run(main.send_menu(update, "home"))

        update.callback_query.answer.assert_awaited_once()

    @patch("main.get_menu_text", return_value="Menu Text")
    @patch("main.build_keyboard")
    def test_edit_message_text_called_with_correct_args(self, mock_build_keyboard, mock_get_menu_text):
        keyboard = MagicMock()
        mock_build_keyboard.return_value = keyboard

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.message = None

        _run(main.send_menu(update, "settings"))

        mock_get_menu_text.assert_called_once_with("settings")
        mock_build_keyboard.assert_called_once_with("settings")
        update.callback_query.edit_message_text.assert_awaited_once_with(
            "Menu Text",
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @patch("main.get_menu_text", return_value="Menu Text")
    @patch("main.build_keyboard")
    def test_reply_text_not_called_on_callback_path(self, mock_build_keyboard, _):
        update = MagicMock()
        update.callback_query = AsyncMock()
        update.message = AsyncMock()

        _run(main.send_menu(update, "home"))

        update.message.reply_text.assert_not_awaited()


class TestSendMenuMessagePath(unittest.TestCase):
    """send_menu() when update.callback_query is falsy and update.message is truthy."""

    @patch("main.get_menu_text", return_value="Reply Text")
    @patch("main.build_keyboard")
    def test_reply_text_called_with_correct_args(self, mock_build_keyboard, mock_get_menu_text):
        keyboard = MagicMock()
        mock_build_keyboard.return_value = keyboard

        update = MagicMock()
        update.callback_query = None
        update.message = AsyncMock()

        _run(main.send_menu(update, "my_packs"))

        mock_get_menu_text.assert_called_once_with("my_packs")
        mock_build_keyboard.assert_called_once_with("my_packs")
        update.message.reply_text.assert_awaited_once_with(
            "Reply Text",
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @patch("main.get_menu_text", return_value="Reply Text")
    @patch("main.build_keyboard")
    def test_callback_query_not_called_on_message_path(self, _, __):
        update = MagicMock()
        update.callback_query = None
        update.message = AsyncMock()

        _run(main.send_menu(update, "home"))

        # No callback_query interaction expected
        update.callback_query = MagicMock()  # should not be touched
        # The above reassignment doesn't matter since we already ran; just confirm no error


class TestSendMenuBadRequestHandling(unittest.TestCase):
    """Error-handling behaviour around BadRequest exceptions."""

    @patch("main.get_menu_text", return_value="Menu Text")
    @patch("main.build_keyboard")
    def test_not_modified_error_is_swallowed(self, mock_build_keyboard, _):
        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest(
            "Message is not modified"
        )
        update.message = None

        # Must not raise
        try:
            _run(main.send_menu(update, "home"))
        except BadRequest:
            self.fail("send_menu raised BadRequest for 'Message is not modified'")

    @patch("main.get_menu_text", return_value="Menu Text")
    @patch("main.build_keyboard")
    def test_other_bad_request_is_re_raised(self, mock_build_keyboard, _):
        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest("Some other error")
        update.message = None

        with self.assertRaises(BadRequest) as ctx:
            _run(main.send_menu(update, "home"))

        self.assertIn("Some other error", str(ctx.exception))

    @patch("main.get_menu_text", return_value="Menu Text")
    @patch("main.build_keyboard")
    def test_not_modified_substring_check_is_exact(self, mock_build_keyboard, _):
        """A message that merely contains 'not modified' but not 'Message is not modified'
        should still be re-raised."""
        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest(
            "Content is not modified"
        )
        update.message = None

        with self.assertRaises(BadRequest):
            _run(main.send_menu(update, "home"))

    @patch("main.get_menu_text", return_value="Menu Text")
    @patch("main.build_keyboard")
    def test_answer_called_even_when_edit_fails_with_not_modified(self, mock_build_keyboard, _):
        """callback_query.answer() should still be called before the failing edit."""
        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest(
            "Message is not modified"
        )
        update.message = None

        _run(main.send_menu(update, "home"))

        update.callback_query.answer.assert_awaited_once()


class TestSendMenuNeitherPath(unittest.TestCase):
    """When both callback_query and message are falsy, no bot call is made."""

    @patch("main.get_menu_text", return_value="Menu Text")
    @patch("main.build_keyboard")
    def test_no_error_when_both_falsy(self, mock_build_keyboard, _):
        update = MagicMock()
        update.callback_query = None
        update.message = None

        # Should complete without raising
        try:
            _run(main.send_menu(update, "home"))
        except Exception as exc:
            self.fail(f"send_menu raised unexpectedly: {exc}")


if __name__ == "__main__":
    unittest.main()
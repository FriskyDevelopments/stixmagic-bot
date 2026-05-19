import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Provide minimal stubbing mechanism modelled after test_main_forge_handlers.py
def _make_stub(name):
    mod = MagicMock()
    mod.__name__ = name
    return mod

def _patch_heavy_imports():
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
                "MenuButtonWebApp", "Update", "WebAppInfo", "ReplyKeyboardMarkup", "ReplyKeyboardRemove", "LabeledPrice"]:
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

import main

class TestMainHelpers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.update = MagicMock()
        self.context = MagicMock()

    def test_pack_namespace_prefix(self):
        with patch('main.get_settings') as mock_get:
            mock_settings = MagicMock()
            mock_settings.is_development = True
            mock_get.return_value = mock_settings
            self.assertEqual(main._pack_namespace_prefix(), "devstix")

            mock_settings.is_development = False
            self.assertEqual(main._pack_namespace_prefix(), "stix")

    def test_cancel_keyboard(self):
        with patch('main.forge_cancel_keyboard', return_value="mocked_kb") as mock_forge:
            kb = main.cancel_keyboard()
            mock_forge.assert_called_once()
            self.assertEqual(kb, "mocked_kb")

    def test_home_keyboard(self):
        kb = main.home_keyboard()
        self.assertIsNotNone(kb)
        self.assertTrue(hasattr(kb, 'inline_keyboard'))
        self.assertEqual(len(kb.inline_keyboard), 1)
        self.assertEqual(kb.inline_keyboard[0][0].callback_data, "nav:home")
        self.assertEqual(kb.inline_keyboard[0][0].text, "✦ Home")

    def test_back_home_keyboard(self):
        kb = main.back_home_keyboard("settings")
        self.assertIsNotNone(kb)
        self.assertTrue(hasattr(kb, 'inline_keyboard'))
        self.assertEqual(len(kb.inline_keyboard), 1)
        self.assertEqual(len(kb.inline_keyboard[0]), 2)
        self.assertEqual(kb.inline_keyboard[0][0].callback_data, "nav:settings")
        self.assertEqual(kb.inline_keyboard[0][1].callback_data, "nav:home")

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_callback_query(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        self.update.callback_query = AsyncMock()
        self.update.message = None

        await main.send_menu(self.update, "test_menu")

        mock_get_menu_text.assert_called_once_with("test_menu")
        mock_build_keyboard.assert_called_once_with("test_menu")
        self.update.callback_query.answer.assert_awaited_once()
        self.update.callback_query.edit_message_text.assert_awaited_once_with(
            "Test Menu",
            reply_markup=mock_build_keyboard.return_value,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_message(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        self.update.callback_query = None
        self.update.message = AsyncMock()

        await main.send_menu(self.update, "test_menu")

        mock_get_menu_text.assert_called_once_with("test_menu")
        mock_build_keyboard.assert_called_once_with("test_menu")
        self.update.message.reply_text.assert_awaited_once_with(
            "Test Menu",
            reply_markup=mock_build_keyboard.return_value,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_callback_query_not_modified_error(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        self.update.callback_query = AsyncMock()
        self.update.message = None

        self.update.callback_query.edit_message_text.side_effect = main.BadRequest("Message is not modified")

        # This should silently catch the exception
        await main.send_menu(self.update, "test_menu")
        self.update.callback_query.edit_message_text.assert_awaited_once()

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_callback_query_other_error(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        self.update.callback_query = AsyncMock()
        self.update.message = None

        self.update.callback_query.edit_message_text.side_effect = main.BadRequest("Other error")

        # This should raise the exception
        with self.assertRaises(main.BadRequest):
            await main.send_menu(self.update, "test_menu")

    @patch('main.send_menu')
    async def test_nav_callback(self, mock_send_menu):
        self.update.callback_query = AsyncMock()
        self.update.callback_query.data = "nav:settings"

        await main.nav_callback(self.update, self.context)

        mock_send_menu.assert_awaited_once_with(self.update, "settings")

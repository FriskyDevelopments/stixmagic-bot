import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

def _make_stub(name):
    mod = MagicMock()
    mod.__name__ = name
    return mod

STUBS = {
    "telegram": _make_stub("telegram"),
    "telegram.ext": _make_stub("telegram.ext"),
    "telegram.error": _make_stub("telegram.error"),
    "PIL": _make_stub("PIL"),
    "PIL.Image": _make_stub("PIL.Image"),
    "PIL.ImageOps": _make_stub("PIL.ImageOps"),
    "dotenv": _make_stub("dotenv"),
}

class StubMock:
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], list):
            self.inline_keyboard = args[0]
        if "inline_keyboard" in kwargs:
            self.inline_keyboard = kwargs["inline_keyboard"]
        if "callback_data" in kwargs:
            self.callback_data = kwargs["callback_data"]
    DEFAULT_TYPE = MagicMock()

for cls in ["InputSticker", "InlineKeyboardButton", "InlineKeyboardMarkup",
            "InlineQueryResultArticle", "InputTextMessageContent",
            "MenuButtonWebApp", "Update", "WebAppInfo"]:
    setattr(STUBS["telegram"], cls, StubMock)

for cls in ["Application", "CallbackQueryHandler", "CommandHandler",
            "ContextTypes", "ConversationHandler", "InlineQueryHandler",
            "MessageHandler"]:
    setattr(STUBS["telegram.ext"], cls, StubMock)

STUBS["telegram.ext"].ConversationHandler.END = -1
STUBS["telegram.ext"].filters = MagicMock()

class BadRequest(Exception):
    pass
STUBS["telegram.error"].BadRequest = BadRequest

class TestMainNav(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.modules_patcher = patch.dict('sys.modules', STUBS)
        self.modules_patcher.start()

        self.local_patcher = patch.dict('sys.modules', {
            'config.runtime': _make_stub('config.runtime'),
            'infra.db': _make_stub('infra.db'),
            'core.engine': _make_stub('core.engine'),
            'domain.media': _make_stub('domain.media'),
            'src.stickers.media': _make_stub('src.stickers.media'),
            'stixmagic.settings': _make_stub('stixmagic.settings'),
            'menus': _make_stub('menus'),
            'packs.db': _make_stub('packs.db'),
            'moderation.guard': _make_stub('moderation.guard'),
            'loaders': _make_stub('loaders'),
            'platforms.telegram': _make_stub('platforms.telegram')
        })
        self.local_patcher.start()

        sys.modules['config.runtime'].get_settings = MagicMock(return_value=MagicMock())
        sys.modules['config.runtime'].ConfigError = Exception
        sys.modules['infra.db'].init_db = MagicMock()

        import main
        self.main = main

    def tearDown(self):
        self.modules_patcher.stop()
        self.local_patcher.stop()

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_callback_query(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.message = None

        await self.main.send_menu(update, 'home')

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once_with(
            "Test Menu", reply_markup=mock_build_keyboard.return_value, parse_mode="HTML", disable_web_page_preview=True
        )

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_callback_query_message_not_modified(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest("Message is not modified")
        update.message = None

        # Should not raise exception
        await self.main.send_menu(update, 'home')

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_callback_query_other_error(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest("Other error")
        update.message = None

        with self.assertRaises(BadRequest):
            await self.main.send_menu(update, 'home')

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()

    @patch('main.get_menu_text')
    @patch('main.build_keyboard')
    async def test_send_menu_message(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = None
        update.message = AsyncMock()

        await self.main.send_menu(update, 'home')

        update.message.reply_text.assert_called_once_with(
            "Test Menu", reply_markup=mock_build_keyboard.return_value, parse_mode="HTML", disable_web_page_preview=True
        )

    @patch('main.send_menu')
    async def test_nav_callback(self, mock_send_menu):
        update = MagicMock()
        update.callback_query = MagicMock()
        update.callback_query.data = "nav:home"
        context = MagicMock()

        await self.main.nav_callback(update, context)

        mock_send_menu.assert_called_once_with(update, "home")

if __name__ == '__main__':
    unittest.main()

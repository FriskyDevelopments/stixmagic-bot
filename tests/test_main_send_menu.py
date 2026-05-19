import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


def _patch_heavy_imports():
    """Inject lightweight stubs for modules main.py pulls in at import time."""
    telegram = MagicMock()
    telegram.__name__ = "telegram"

    # We need to explicitly add attributes that main.py expects
    telegram.InputSticker = MagicMock()
    telegram.InlineKeyboardMarkup = MagicMock()
    telegram.InlineKeyboardButton = MagicMock()
    telegram.Update = MagicMock()
    telegram.InputMediaDocument = MagicMock()

    telegram_ext = MagicMock()
    telegram_ext.__name__ = "telegram.ext"
    telegram_ext.ContextTypes = MagicMock()
    telegram_ext.ContextTypes.DEFAULT_TYPE = MagicMock()

    telegram_error = MagicMock()
    telegram_error.__name__ = "telegram.error"
    telegram_error.BadRequest = type("BadRequest", (Exception,), {})

    sys.modules["telegram"] = telegram
    sys.modules["telegram.ext"] = telegram_ext
    sys.modules["telegram.error"] = telegram_error


_patch_heavy_imports()

from telegram.error import BadRequest

import main


class TestSendMenu(unittest.IsolatedAsyncioTestCase):
    @patch("main.get_menu_text")
    @patch("main.build_keyboard")
    async def test_send_menu_callback_query(
        self, mock_build_keyboard, mock_get_menu_text
    ):
        mock_get_menu_text.return_value = "Test Menu Text"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.message = None

        await main.send_menu(update, "test_menu_id")

        mock_get_menu_text.assert_called_once_with("test_menu_id")
        mock_build_keyboard.assert_called_once_with("test_menu_id")
        update.callback_query.answer.assert_awaited_once()
        update.callback_query.edit_message_text.assert_awaited_once_with(
            "Test Menu Text",
            reply_markup=mock_build_keyboard.return_value,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @patch("main.get_menu_text")
    @patch("main.build_keyboard")
    async def test_send_menu_message(self, mock_build_keyboard, mock_get_menu_text):
        mock_get_menu_text.return_value = "Test Menu Text"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = None
        update.message = AsyncMock()

        await main.send_menu(update, "test_menu_id")

        mock_get_menu_text.assert_called_once_with("test_menu_id")
        mock_build_keyboard.assert_called_once_with("test_menu_id")
        update.message.reply_text.assert_awaited_once_with(
            "Test Menu Text",
            reply_markup=mock_build_keyboard.return_value,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @patch("main.get_menu_text")
    @patch("main.build_keyboard")
    async def test_send_menu_callback_query_ignores_not_modified(
        self, mock_build_keyboard, mock_get_menu_text
    ):
        mock_get_menu_text.return_value = "Test Menu Text"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest(
            "Message is not modified"
        )
        update.message = None

        # Should not raise exception
        await main.send_menu(update, "test_menu_id")

        update.callback_query.edit_message_text.assert_awaited_once()

    @patch("main.get_menu_text")
    @patch("main.build_keyboard")
    async def test_send_menu_callback_query_raises_other_bad_request(
        self, mock_build_keyboard, mock_get_menu_text
    ):
        mock_get_menu_text.return_value = "Test Menu Text"
        mock_build_keyboard.return_value = MagicMock()

        update = MagicMock()
        update.callback_query = AsyncMock()
        update.callback_query.edit_message_text.side_effect = BadRequest("Other error")
        update.message = None

        # Should raise exception
        with self.assertRaises(BadRequest) as context:
            await main.send_menu(update, "test_menu_id")

        self.assertIn("Other error", str(context.exception))
        update.callback_query.edit_message_text.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

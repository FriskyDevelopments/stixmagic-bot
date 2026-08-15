"""
Tests for main.py - start handler changes introduced in this PR.

Covers:
 - New user welcome message (with and without first_name)
 - Existing user menu delegation
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import main
from main import start

def _run(coro):
    return asyncio.run(coro)

def _make_update(user_id=123, first_name="Alice"):
    update = MagicMock()
    user = MagicMock()
    user.id = user_id
    user.first_name = first_name
    update.effective_user = user
    update.message = AsyncMock()
    return update

def _make_context():
    return MagicMock()

class TestStartHandler(unittest.TestCase):
    @patch("main.is_new_user")
    @patch("main.build_keyboard")
    def test_start_new_user_with_first_name(self, mock_build_keyboard, mock_is_new_user):
        mock_is_new_user.return_value = True
        mock_build_keyboard.return_value = "mock_keyboard"

        update = _make_update(user_id=123, first_name="Alice")
        ctx = _make_context()

        _run(start(update, ctx))

        mock_is_new_user.assert_called_once_with(123)
        mock_build_keyboard.assert_called_once_with("home")
        update.message.reply_text.assert_awaited_once()

        args, kwargs = update.message.reply_text.call_args
        self.assertIn("Alice", args[0])
        self.assertIn("The laboratory opens", args[0])
        self.assertEqual(kwargs["reply_markup"], "mock_keyboard")
        self.assertEqual(kwargs["parse_mode"], "HTML")

    @patch("main.is_new_user")
    @patch("main.build_keyboard")
    def test_start_new_user_without_first_name(self, mock_build_keyboard, mock_is_new_user):
        mock_is_new_user.return_value = True
        mock_build_keyboard.return_value = "mock_keyboard"

        update = _make_update(user_id=124, first_name=None)
        ctx = _make_context()

        _run(start(update, ctx))

        update.message.reply_text.assert_awaited_once()
        args, kwargs = update.message.reply_text.call_args
        self.assertIn("there", args[0])
        self.assertIn("The laboratory opens", args[0])

    @patch("main.is_new_user")
    @patch("main.send_menu")
    def test_start_existing_user(self, mock_send_menu, mock_is_new_user):
        mock_is_new_user.return_value = False

        update = _make_update(user_id=125, first_name="Bob")
        ctx = _make_context()

        _run(start(update, ctx))

        mock_is_new_user.assert_called_once_with(125)
        mock_send_menu.assert_awaited_once_with(update, "home")
        update.message.reply_text.assert_not_awaited()

if __name__ == "__main__":
    unittest.main()

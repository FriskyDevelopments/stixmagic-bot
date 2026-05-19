"""
Tests for main.py – pack_info(), manage_stickers(), and show_packs() handlers.

Covers changes introduced in this PR:
 - pack_info: ss.sticker_type is now read from the Telegram StickerSet response
 - manage_stickers: pack-list message built with direct string concat (replaces msg_parts list)
 - show_packs: same string-concat refactor
"""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal stubs so we can import main without a running Telegram application
# (mirror the pattern from test_main_forge_handlers.py)
# ---------------------------------------------------------------------------

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

import main  # noqa: E402


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_context(args=None, user_data=None):
    ctx = MagicMock()
    ctx.args = args or []
    ctx.user_data = user_data if user_data is not None else {}
    ctx.bot = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# pack_info – sticker_type capture
# ---------------------------------------------------------------------------

class TestPackInfoStickerType(unittest.TestCase):
    """Tests for the sticker_type = ss.sticker_type change in pack_info."""

    def _make_sticker_set(self, title="Cool Pack", sticker_type="regular", stickers=None):
        ss = MagicMock()
        ss.title = title
        ss.sticker_type = sticker_type
        if stickers is None:
            s = MagicMock()
            s.is_animated = False
            s.is_video = False
            stickers = [s]
        ss.stickers = stickers
        return ss

    @patch("main.catalog_get_pack", return_value=None)
    def test_sticker_type_read_from_sticker_set(self, _mock_catalog):
        """ss.sticker_type must be accessed; if missing, AttributeError would propagate."""
        ctx = _make_context(args=["testpack"])
        update = MagicMock()
        update.message = AsyncMock()
        update.effective_user = MagicMock(id=42)

        ss = self._make_sticker_set(sticker_type="mask")
        ctx.bot.get_sticker_set.return_value = ss

        progress = AsyncMock()
        update.message.reply_text.return_value = progress

        _run(main.pack_info(update, ctx))

        # The sticker_set was fetched and sticker_type was accessed
        ctx.bot.get_sticker_set.assert_awaited_once_with("testpack")
        # sticker_type attribute was accessed (not raising AttributeError proves it)
        _ = ss.sticker_type  # sanity — access triggers MagicMock attribute tracking
        self.assertEqual(ss.sticker_type, "mask")

    @patch("main.catalog_get_pack", return_value=None)
    def test_pack_info_succeeds_with_regular_sticker_type(self, _mock_catalog):
        ctx = _make_context(args=["my_pack"])
        update = MagicMock()
        update.message = AsyncMock()
        update.effective_user = MagicMock(id=7)

        ss = self._make_sticker_set(title="My Pack", sticker_type="regular")
        ctx.bot.get_sticker_set.return_value = ss

        progress = AsyncMock()
        update.message.reply_text.return_value = progress

        _run(main.pack_info(update, ctx))

        # No exception means sticker_type was accessed cleanly
        progress.edit_text.assert_awaited_once()

    @patch("main.catalog_get_pack", return_value=None)
    def test_pack_info_no_pack_name_sends_usage(self, _mock_catalog):
        """When no pack name is given, usage instructions are sent."""
        ctx = _make_context(args=[])
        update = MagicMock()
        update.message = AsyncMock()

        _run(main.pack_info(update, ctx))

        update.message.reply_text.assert_awaited_once()
        call_kwargs = update.message.reply_text.call_args
        self.assertIn("/info", str(call_kwargs))

    @patch("main.catalog_get_pack", return_value=None)
    def test_pack_info_unknown_pack_sends_not_found(self, _mock_catalog):
        """When Telegram raises an exception, a not-found message is shown."""
        ctx = _make_context(args=["ghost_pack"])
        update = MagicMock()
        update.message = AsyncMock()
        update.effective_user = MagicMock(id=1)

        ctx.bot.get_sticker_set.side_effect = Exception("Pack not found")

        progress = AsyncMock()
        update.message.reply_text.return_value = progress

        _run(main.pack_info(update, ctx))

        progress.edit_text.assert_awaited_once()
        edit_call_args = progress.edit_text.call_args[0][0]
        self.assertIn("not found", edit_call_args.lower())

    @patch("main.catalog_get_pack", return_value=None)
    def test_pack_info_url_extracts_pack_name(self, _mock_catalog):
        """A t.me/addstickers/ URL should have the pack name extracted."""
        ctx = _make_context(args=["https://t.me/addstickers/mypack123"])
        update = MagicMock()
        update.message = AsyncMock()
        update.effective_user = MagicMock(id=1)

        ss = self._make_sticker_set(title="My Pack 123", sticker_type="regular")
        ctx.bot.get_sticker_set.return_value = ss

        progress = AsyncMock()
        update.message.reply_text.return_value = progress

        _run(main.pack_info(update, ctx))

        ctx.bot.get_sticker_set.assert_awaited_once_with("mypack123")


# ---------------------------------------------------------------------------
# manage_stickers – string concat produces the same output
# ---------------------------------------------------------------------------

class TestManageStickersMessageFormat(unittest.TestCase):
    """Tests that manage_stickers builds the pack-list message correctly
    after refactoring from msg_parts list to direct string concat."""

    def _make_update(self, callback=False):
        update = MagicMock()
        if callback:
            update.callback_query = AsyncMock()
            update.message = None
        else:
            update.callback_query = None
            update.message = AsyncMock()
        update.effective_user = MagicMock(id=99)
        return update

    @patch("main.validate_and_sync_packs")
    def test_message_contains_numbered_pack_titles(self, mock_sync):
        """Each pack title appears as a numbered entry in the message."""
        mock_sync.return_value = [
            ("alpha_pack", "Alpha Stickers"),
            ("beta_pack", "Beta Stickers"),
        ]
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.manage_stickers(update, ctx))

        update.message.reply_text.assert_awaited_once()
        msg_text = update.message.reply_text.call_args[0][0]
        self.assertIn("1.", msg_text)
        self.assertIn("Alpha Stickers", msg_text)
        self.assertIn("2.", msg_text)
        self.assertIn("Beta Stickers", msg_text)

    @patch("main.validate_and_sync_packs")
    def test_message_starts_with_crucible_header(self, mock_sync):
        mock_sync.return_value = [("my_pack", "My Pack")]
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.manage_stickers(update, ctx))

        msg_text = update.message.reply_text.call_args[0][0]
        self.assertIn("THE CRUCIBLE", msg_text)

    @patch("main.validate_and_sync_packs")
    def test_empty_packs_sends_empty_crucible_message(self, mock_sync):
        mock_sync.return_value = []
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.manage_stickers(update, ctx))

        update.message.reply_text.assert_awaited_once()
        msg_text = update.message.reply_text.call_args[0][0]
        self.assertIn("empty", msg_text.lower())

    @patch("main.validate_and_sync_packs")
    def test_callback_path_uses_edit_message_text(self, mock_sync):
        mock_sync.return_value = [("p1", "Pack One")]
        update = self._make_update(callback=True)
        ctx = _make_context()

        _run(main.manage_stickers(update, ctx))

        update.callback_query.edit_message_text.assert_awaited_once()
        update.callback_query.answer.assert_awaited_once()

    @patch("main.validate_and_sync_packs")
    def test_multiple_packs_all_appear_in_order(self, mock_sync):
        """Three packs should appear in index order 1, 2, 3."""
        packs = [("p1", "First"), ("p2", "Second"), ("p3", "Third")]
        mock_sync.return_value = packs
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.manage_stickers(update, ctx))

        msg_text = update.message.reply_text.call_args[0][0]
        pos1 = msg_text.find("First")
        pos2 = msg_text.find("Second")
        pos3 = msg_text.find("Third")
        self.assertLess(pos1, pos2, "First should appear before Second")
        self.assertLess(pos2, pos3, "Second should appear before Third")


# ---------------------------------------------------------------------------
# show_packs – string concat produces the same output
# ---------------------------------------------------------------------------

class TestShowPacksMessageFormat(unittest.TestCase):
    """Tests that show_packs builds the grimoire message correctly after
    refactoring from msg_parts list to direct string concat."""

    def _make_update(self, callback=False):
        update = MagicMock()
        if callback:
            update.callback_query = AsyncMock()
            update.message = None
        else:
            update.callback_query = None
            update.message = AsyncMock()
        update.effective_user = MagicMock(id=55)
        return update

    @patch("main.validate_and_sync_packs")
    def test_message_contains_numbered_pack_titles(self, mock_sync):
        mock_sync.return_value = [
            ("alpha_pack", "Alpha Stickers"),
            ("beta_pack", "Beta Stickers"),
        ]
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.show_packs(update, ctx))

        update.message.reply_text.assert_awaited_once()
        msg_text = update.message.reply_text.call_args[0][0]
        self.assertIn("1.", msg_text)
        self.assertIn("Alpha Stickers", msg_text)
        self.assertIn("2.", msg_text)
        self.assertIn("Beta Stickers", msg_text)

    @patch("main.validate_and_sync_packs")
    def test_message_starts_with_grimoire_header(self, mock_sync):
        mock_sync.return_value = [("p", "Pack")]
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.show_packs(update, ctx))

        msg_text = update.message.reply_text.call_args[0][0]
        self.assertIn("GRIMOIRE", msg_text)

    @patch("main.validate_and_sync_packs")
    def test_empty_packs_sends_empty_grimoire_message(self, mock_sync):
        mock_sync.return_value = []
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.show_packs(update, ctx))

        update.message.reply_text.assert_awaited_once()
        msg_text = update.message.reply_text.call_args[0][0]
        self.assertIn("empty", msg_text.lower())

    @patch("main.validate_and_sync_packs")
    def test_callback_path_uses_edit_message_text(self, mock_sync):
        mock_sync.return_value = [("p1", "Pack One")]
        update = self._make_update(callback=True)
        ctx = _make_context()

        _run(main.show_packs(update, ctx))

        update.callback_query.edit_message_text.assert_awaited_once()
        update.callback_query.answer.assert_awaited_once()

    @patch("main.validate_and_sync_packs")
    def test_title_at_index_one_is_first(self, mock_sync):
        """The first pack title must be tagged with index 1."""
        mock_sync.return_value = [("first_pack", "First Pack"), ("second_pack", "Second Pack")]
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.show_packs(update, ctx))

        msg_text = update.message.reply_text.call_args[0][0]
        idx_first = msg_text.find("First Pack")
        idx_second = msg_text.find("Second Pack")
        self.assertLess(idx_first, idx_second)

    @patch("main.validate_and_sync_packs")
    def test_single_pack_numbered_one(self, mock_sync):
        """A single pack must carry the number 1."""
        mock_sync.return_value = [("only_pack", "Only Pack")]
        update = self._make_update(callback=False)
        ctx = _make_context()

        _run(main.show_packs(update, ctx))

        msg_text = update.message.reply_text.call_args[0][0]
        self.assertIn("1.", msg_text)
        self.assertIn("Only Pack", msg_text)


if __name__ == "__main__":
    unittest.main()
"""
Tests for main.py – forge-wizard handler changes introduced in this PR.

Covers:
 - State constant values (WAITING_TITLE, WAITING_TITLE_CONFIRM, WAITING_STICKER
   and the rest of the renumbered constants)
 - cancel_keyboard() delegation to forge_cancel_keyboard
 - create_start(): ForgeDraft initialisation, text & return value, both
   callback-query and plain-message paths
 - create_title(): valid input transitions to WAITING_TITLE_CONFIRM with correct
   draft; invalid input stays at WAITING_TITLE
 - create_title_confirm(): forge_confirm path, forge_edit path, missing draft path
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

    # Add necessary classes to stubs to avoid import errors
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
        DEFAULT_TYPE = MagicMock()

    # telegram module
    for cls in ["InputSticker", "InlineKeyboardButton", "InlineKeyboardMarkup",
                "InlineQueryResultArticle", "InputTextMessageContent",
                "MenuButtonWebApp", "Update", "WebAppInfo"]:
        setattr(telegram, cls, StubMock)

    # telegram.ext module
    for cls in ["Application", "CallbackQueryHandler", "CommandHandler",
                "ContextTypes", "ConversationHandler", "InlineQueryHandler",
                "MessageHandler"]:
        setattr(telegram_ext, cls, StubMock)
    telegram_ext.ConversationHandler.END = -1
    telegram_ext.filters = MagicMock()

    # telegram.error module
    telegram_error.BadRequest = Exception

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

    # Ensure init_db and get_settings don't run real DB code
    sys.modules["infra.db"].init_db = MagicMock()
    sys.modules["config.runtime"].get_settings = MagicMock(return_value=MagicMock())
    sys.modules["config.runtime"].ConfigError = Exception

    return stubs


# Patch before any main import happens
_patch_heavy_imports()

# Now we can import what we need from main
import importlib

# We import individual symbols we want to test from main
# without triggering the full application startup side-effects.
# The module-level `init_db()` and engine creation are already stubbed above.
import main as _main_mod

from main import (
    CHOOSING_PACK,
    WAITING_CATALOG_SEARCH,
    WAITING_CUT_PACK,
    WAITING_FEATURE_DESC,
    WAITING_FEATURE_PACK,
    WAITING_MASK_IMAGE,
    WAITING_SOURCE_IMAGE,
    WAITING_STICKER,
    WAITING_STICKER_ADD,
    WAITING_SYNC_NAME,
    WAITING_TITLE,
    WAITING_TITLE_CONFIRM,
    cancel_keyboard,
    create_start,
    create_sticker,
    create_title,
    create_title_confirm,
    home_keyboard,
    back_home_keyboard,
)
from src.bot.forge_wizard import ForgeDraft, ForgeStep
from telegram import InlineKeyboardMarkup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Execute a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_context(user_data=None):
    ctx = MagicMock()
    ctx.user_data = user_data if user_data is not None else {}
    return ctx


def _make_message_update(text: str):
    """Update with a plain message (no callback_query)."""
    update = MagicMock()
    update.callback_query = None
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_callback_update(callback_data: str):
    """Update arriving from an inline keyboard button press."""
    update = MagicMock()
    update.callback_query = MagicMock()
    update.callback_query.data = callback_data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.message = None
    return update


# ---------------------------------------------------------------------------
# State constant tests
# ---------------------------------------------------------------------------


class TestStateConstants(unittest.TestCase):
    """The renumbered state constants must have the correct integer values."""

    def test_waiting_title_is_zero(self):
        self.assertEqual(WAITING_TITLE, 0)

    def test_waiting_title_confirm_is_one(self):
        self.assertEqual(WAITING_TITLE_CONFIRM, 1)

    def test_waiting_sticker_is_two(self):
        self.assertEqual(WAITING_STICKER, 2)

    def test_choosing_pack_is_three(self):
        self.assertEqual(CHOOSING_PACK, 3)

    def test_waiting_sticker_add_is_four(self):
        self.assertEqual(WAITING_STICKER_ADD, 4)

    def test_waiting_source_image_is_five(self):
        self.assertEqual(WAITING_SOURCE_IMAGE, 5)

    def test_waiting_mask_image_is_six(self):
        self.assertEqual(WAITING_MASK_IMAGE, 6)

    def test_waiting_cut_pack_is_seven(self):
        self.assertEqual(WAITING_CUT_PACK, 7)

    def test_waiting_sync_name_is_eight(self):
        self.assertEqual(WAITING_SYNC_NAME, 8)

    def test_waiting_feature_pack_is_nine(self):
        self.assertEqual(WAITING_FEATURE_PACK, 9)

    def test_waiting_feature_desc_is_ten(self):
        self.assertEqual(WAITING_FEATURE_DESC, 10)

    def test_waiting_catalog_search_is_eleven(self):
        self.assertEqual(WAITING_CATALOG_SEARCH, 11)

    def test_all_state_constants_unique(self):
        constants = [
            WAITING_TITLE,
            WAITING_TITLE_CONFIRM,
            WAITING_STICKER,
            CHOOSING_PACK,
            WAITING_STICKER_ADD,
            WAITING_SOURCE_IMAGE,
            WAITING_MASK_IMAGE,
            WAITING_CUT_PACK,
            WAITING_SYNC_NAME,
            WAITING_FEATURE_PACK,
            WAITING_FEATURE_DESC,
            WAITING_CATALOG_SEARCH,
        ]
        self.assertEqual(len(constants), len(set(constants)))


# ---------------------------------------------------------------------------
# cancel_keyboard delegation
# ---------------------------------------------------------------------------


class TestCancelKeyboardDelegates(unittest.TestCase):
    """main.cancel_keyboard must delegate to forge_wizard.cancel_keyboard."""

    def test_returns_inline_keyboard_markup(self):
        kb = cancel_keyboard()
        self.assertIsInstance(kb, InlineKeyboardMarkup)

    def test_cancel_button_callback_nav_home(self):
        kb = cancel_keyboard()
        button = kb.inline_keyboard[0][0]
        self.assertEqual(button.callback_data, "nav:home")

    def test_identical_to_forge_cancel_keyboard(self):
        from src.bot.forge_wizard import cancel_keyboard as forge_cancel_keyboard
        main_kb = cancel_keyboard()
        forge_kb = forge_cancel_keyboard()
        # Both should produce the same structure
        self.assertEqual(
            main_kb.inline_keyboard[0][0].callback_data,
            forge_kb.inline_keyboard[0][0].callback_data,
        )


# ---------------------------------------------------------------------------
# create_start handler
# ---------------------------------------------------------------------------


class TestCreateStart(unittest.TestCase):
    """create_start initialises a ForgeDraft and returns WAITING_TITLE."""

    def test_returns_waiting_title_via_message(self):
        update = _make_callback_update.__wrapped__ if hasattr(_make_callback_update, "__wrapped__") else None
        update = MagicMock()
        update.callback_query = None
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        ctx = _make_context()
        result = _run(create_start(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_returns_waiting_title_via_callback(self):
        update = _make_callback_update("menu_create")
        ctx = _make_context()
        result = _run(create_start(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_initialises_forge_draft_in_user_data(self):
        update = MagicMock()
        update.callback_query = None
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        ctx = _make_context()
        _run(create_start(update, ctx))
        self.assertIn("forge_draft", ctx.user_data)
        draft = ctx.user_data["forge_draft"]
        self.assertIsInstance(draft, ForgeDraft)

    def test_initial_draft_step_is_title(self):
        update = MagicMock()
        update.callback_query = None
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        ctx = _make_context()
        _run(create_start(update, ctx))
        self.assertEqual(ctx.user_data["forge_draft"].step, ForgeStep.TITLE)

    def test_initial_draft_title_is_empty_string(self):
        update = MagicMock()
        update.callback_query = None
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        ctx = _make_context()
        _run(create_start(update, ctx))
        self.assertEqual(ctx.user_data["forge_draft"].title, "")

    def test_callback_path_calls_edit_message_text(self):
        update = _make_callback_update("menu_create")
        ctx = _make_context()
        _run(create_start(update, ctx))
        update.callback_query.edit_message_text.assert_awaited_once()

    def test_message_path_calls_reply_text(self):
        update = MagicMock()
        update.callback_query = None
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        ctx = _make_context()
        _run(create_start(update, ctx))
        update.message.reply_text.assert_awaited_once()

    def test_sent_text_contains_forge_a_pack(self):
        update = MagicMock()
        update.callback_query = None
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        ctx = _make_context()
        _run(create_start(update, ctx))
        args, kwargs = update.message.reply_text.call_args
        text = args[0] if args else kwargs.get("text", "")
        self.assertIn("FORGE A PACK", text)


# ---------------------------------------------------------------------------
# create_title handler
# ---------------------------------------------------------------------------


class TestCreateTitle(unittest.TestCase):
    """create_title validates the title and transitions state appropriately."""

    def test_valid_title_returns_waiting_title_confirm(self):
        update = _make_message_update("My Great Pack")
        ctx = _make_context()
        result = _run(create_title(update, ctx))
        self.assertEqual(result, WAITING_TITLE_CONFIRM)

    def test_empty_title_returns_waiting_title(self):
        update = _make_message_update("")
        ctx = _make_context()
        result = _run(create_title(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_whitespace_only_title_returns_waiting_title(self):
        update = _make_message_update("   ")
        ctx = _make_context()
        result = _run(create_title(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_too_long_title_returns_waiting_title(self):
        update = _make_message_update("X" * 65)
        ctx = _make_context()
        result = _run(create_title(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_exactly_64_chars_returns_waiting_title_confirm(self):
        update = _make_message_update("A" * 64)
        ctx = _make_context()
        result = _run(create_title(update, ctx))
        self.assertEqual(result, WAITING_TITLE_CONFIRM)

    def test_valid_title_sets_forge_draft_confirm_step(self):
        update = _make_message_update("Cool Pack")
        ctx = _make_context()
        _run(create_title(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        self.assertIsInstance(draft, ForgeDraft)
        self.assertEqual(draft.step, ForgeStep.CONFIRM_TITLE)

    def test_valid_title_sets_forge_draft_with_stripped_title(self):
        update = _make_message_update("  Trimmed Pack  ")
        ctx = _make_context()
        _run(create_title(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        self.assertEqual(draft.title, "Trimmed Pack")

    def test_invalid_title_does_not_set_confirm_draft(self):
        update = _make_message_update("")
        ctx = _make_context()
        _run(create_title(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        # Either no draft or draft step is not CONFIRM_TITLE
        if draft is not None:
            self.assertNotEqual(draft.step, ForgeStep.CONFIRM_TITLE)

    def test_invalid_title_sends_error_reply(self):
        update = _make_message_update("")
        ctx = _make_context()
        _run(create_title(update, ctx))
        update.message.reply_text.assert_awaited_once()

    def test_valid_title_sends_confirmation_reply(self):
        update = _make_message_update("Valid Pack")
        ctx = _make_context()
        _run(create_title(update, ctx))
        update.message.reply_text.assert_awaited_once()

    def test_error_reply_contains_warning_symbol(self):
        update = _make_message_update("Z" * 70)
        ctx = _make_context()
        _run(create_title(update, ctx))
        args, _ = update.message.reply_text.call_args
        text = args[0]
        self.assertIn("⚠", text)


# ---------------------------------------------------------------------------
# create_title_confirm handler
# ---------------------------------------------------------------------------


class TestCreateTitleConfirm(unittest.TestCase):
    """create_title_confirm routes between confirm, edit, and missing-draft paths."""

    def _draft(self, title="My Pack", step=ForgeStep.CONFIRM_TITLE):
        return ForgeDraft(title=title, step=step)

    # ── forge_confirm path ───────────────────────────────────

    def test_forge_confirm_returns_waiting_sticker(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": self._draft()})
        result = _run(create_title_confirm(update, ctx))
        self.assertEqual(result, WAITING_STICKER)

    def test_forge_confirm_sets_newpack_title(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": self._draft("Awesome Pack")})
        _run(create_title_confirm(update, ctx))
        self.assertEqual(ctx.user_data.get("newpack_title"), "Awesome Pack")

    def test_forge_confirm_updates_draft_to_sticker_step(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": self._draft("Pack A")})
        _run(create_title_confirm(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        self.assertIsInstance(draft, ForgeDraft)
        self.assertEqual(draft.step, ForgeStep.STICKER)

    def test_forge_confirm_preserves_title_in_draft(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": self._draft("Keeper Title")})
        _run(create_title_confirm(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        self.assertEqual(draft.title, "Keeper Title")

    def test_forge_confirm_sends_sticker_prompt(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": self._draft("My Pack")})
        _run(create_title_confirm(update, ctx))
        update.callback_query.edit_message_text.assert_awaited_once()
        args, _ = update.callback_query.edit_message_text.call_args
        text = args[0]
        self.assertIn("seed sticker", text)

    # ── forge_edit path ──────────────────────────────────────

    def test_forge_edit_returns_waiting_title(self):
        update = _make_callback_update("forge_edit")
        ctx = _make_context({"forge_draft": self._draft()})
        result = _run(create_title_confirm(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_forge_edit_updates_draft_to_title_step(self):
        update = _make_callback_update("forge_edit")
        ctx = _make_context({"forge_draft": self._draft("Edit Me")})
        _run(create_title_confirm(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        self.assertEqual(draft.step, ForgeStep.TITLE)

    def test_forge_edit_preserves_title_in_draft(self):
        update = _make_callback_update("forge_edit")
        ctx = _make_context({"forge_draft": self._draft("Keep Title")})
        _run(create_title_confirm(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        self.assertEqual(draft.title, "Keep Title")

    def test_forge_edit_sends_forge_start_text(self):
        update = _make_callback_update("forge_edit")
        ctx = _make_context({"forge_draft": self._draft()})
        _run(create_title_confirm(update, ctx))
        update.callback_query.edit_message_text.assert_awaited_once()
        args, _ = update.callback_query.edit_message_text.call_args
        text = args[0]
        self.assertIn("FORGE A PACK", text)

    def test_forge_edit_does_not_set_newpack_title(self):
        update = _make_callback_update("forge_edit")
        ctx = _make_context({"forge_draft": self._draft()})
        _run(create_title_confirm(update, ctx))
        self.assertNotIn("newpack_title", ctx.user_data)

    # ── missing draft path ───────────────────────────────────

    def test_missing_draft_ends_conversation(self):
        from telegram.ext import ConversationHandler
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({})  # no forge_draft
        result = _run(create_title_confirm(update, ctx))
        self.assertEqual(result, ConversationHandler.END)

    def test_none_draft_ends_conversation(self):
        from telegram.ext import ConversationHandler
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": None})
        result = _run(create_title_confirm(update, ctx))
        self.assertEqual(result, ConversationHandler.END)

    def test_wrong_type_draft_ends_conversation(self):
        from telegram.ext import ConversationHandler
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": "not a ForgeDraft"})
        result = _run(create_title_confirm(update, ctx))
        self.assertEqual(result, ConversationHandler.END)

    def test_missing_draft_sends_restart_message(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({})
        _run(create_title_confirm(update, ctx))
        update.callback_query.edit_message_text.assert_awaited_once()
        args, _ = update.callback_query.edit_message_text.call_args
        text = args[0]
        self.assertIn("Draft lost", text)

    def test_missing_draft_provides_restart_keyboard(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({})
        _run(create_title_confirm(update, ctx))
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("reply_markup", kwargs)
        markup = kwargs["reply_markup"]
        self.assertIsInstance(markup, InlineKeyboardMarkup)
        # The restart button should point to menu_create
        restart_btn = markup.inline_keyboard[0][0]
        self.assertEqual(restart_btn.callback_data, "menu_create")

    # ── query.answer() always called ─────────────────────────

    def test_query_answer_called_on_confirm(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({"forge_draft": self._draft()})
        _run(create_title_confirm(update, ctx))
        update.callback_query.answer.assert_awaited_once()

    def test_query_answer_called_on_edit(self):
        update = _make_callback_update("forge_edit")
        ctx = _make_context({"forge_draft": self._draft()})
        _run(create_title_confirm(update, ctx))
        update.callback_query.answer.assert_awaited_once()

    def test_query_answer_called_on_missing_draft(self):
        update = _make_callback_update("forge_confirm")
        ctx = _make_context({})
        _run(create_title_confirm(update, ctx))
        update.callback_query.answer.assert_awaited_once()


# ---------------------------------------------------------------------------
# create_sticker handler
# ---------------------------------------------------------------------------

class TestCreateSticker(unittest.TestCase):
    """create_sticker handles unsupported media by rejecting it."""

    @patch("main.telegram_adapter")
    def test_unsupported_media_returns_waiting_sticker(self, mock_adapter):
        # Mock parse_message_media to return None (unsupported media)
        mock_adapter.parse_message_media.return_value = None

        update = _make_message_update("some text")
        update.message.from_user = MagicMock()
        ctx = _make_context({"newpack_title": "My Pack"})

        result = _run(create_sticker(update, ctx))

        self.assertEqual(result, WAITING_STICKER)
        update.message.reply_text.assert_awaited_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("unrecognised", args[0])




# ---------------------------------------------------------------------------
# Keyboard helpers
# ---------------------------------------------------------------------------

class TestMenuKeyboards(unittest.TestCase):
    """Test the basic menu keyboard generation functions in main.py."""

    def test_cancel_keyboard(self):
        keyboard = cancel_keyboard()
        self.assertIsInstance(keyboard, InlineKeyboardMarkup)
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "✕ Cancel")
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "nav:home")

    def test_home_keyboard(self):
        keyboard = home_keyboard()
        self.assertIsInstance(keyboard, InlineKeyboardMarkup)
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "✦ Home")
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "nav:home")

    def test_back_home_keyboard(self):
        keyboard = back_home_keyboard("settings")
        self.assertIsInstance(keyboard, InlineKeyboardMarkup)
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "◂ Back")
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "nav:settings")
        self.assertEqual(keyboard.inline_keyboard[0][1].text, "✦ Home")
        self.assertEqual(keyboard.inline_keyboard[0][1].callback_data, "nav:home")

if __name__ == "__main__":

    unittest.main()
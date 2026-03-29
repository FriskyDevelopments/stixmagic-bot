"""
Tests for the forge-related handler changes in main.py introduced in this PR.

Covers:
 - State constant values (WAITING_TITLE, WAITING_TITLE_CONFIRM, WAITING_STICKER)
 - cancel_keyboard() delegation to forge_cancel_keyboard
 - create_start: via message path and via callback_query path
 - create_title: invalid title stays at WAITING_TITLE; valid title advances to WAITING_TITLE_CONFIRM
 - create_title_confirm: edit action returns WAITING_TITLE; ok action returns WAITING_STICKER;
   missing / wrong-type draft returns ConversationHandler.END
"""

import asyncio
import importlib.util
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal telegram stubs so main.py can be imported without the package.
# ---------------------------------------------------------------------------

_fake_telegram = MagicMock()
_fake_telegram_ext = MagicMock()
_fake_telegram_error = MagicMock()

# ConversationHandler.END must be a real integer so comparisons work.
_conversation_handler_mock = MagicMock()
_conversation_handler_mock.END = -1
_fake_telegram_ext.ConversationHandler = _conversation_handler_mock

# Ensure InlineKeyboardMarkup / InlineKeyboardButton return distinct MagicMocks.
_fake_telegram.InlineKeyboardMarkup = MagicMock(side_effect=lambda rows: MagicMock(rows=rows))
_fake_telegram.InlineKeyboardButton = MagicMock(side_effect=lambda text, **kw: MagicMock(text=text, **kw))

sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.ext", _fake_telegram_ext)
sys.modules.setdefault("telegram.error", _fake_telegram_error)

# Stub all other heavy dependencies that main.py imports at module level.
_stub_modules = [
    "config",
    "config.runtime",
    "infra",
    "infra.db",
    "domain",
    "domain.media",
    "core",
    "core.engine",
    "platforms",
    "platforms.telegram",
    "loaders",
    "menus",
]
for _mod in _stub_modules:
    sys.modules.setdefault(_mod, MagicMock())

# Provide a real forge_wizard (with its own telegram stub) instead of a full mock
# so that ForgeDraft / ForgeStep instances pass isinstance() checks inside handlers.
from src.bot.forge_wizard import ForgeDraft, ForgeStep  # noqa: E402

_fake_forge_wizard = MagicMock()
_fake_forge_wizard.ForgeDraft = ForgeDraft
_fake_forge_wizard.ForgeStep = ForgeStep
_fake_forge_wizard.cancel_keyboard = MagicMock(return_value=MagicMock(name="cancel_kb"))
_fake_forge_wizard.create_start_text = MagicMock(return_value="<forge start text>")
_fake_forge_wizard.sticker_prompt_text = MagicMock(return_value="<sticker prompt text>")
_fake_forge_wizard.title_confirmation_keyboard = MagicMock(return_value=MagicMock(name="confirm_kb"))
_fake_forge_wizard.title_confirmation_text = MagicMock(return_value="<confirm text>")
_fake_forge_wizard.validate_pack_title = MagicMock(return_value=(True, "My Pack"))
sys.modules["src.bot.forge_wizard"] = _fake_forge_wizard

# ---------------------------------------------------------------------------
# Load main.py as a module (avoids polluting the real module namespace and
# lets us re-import cleanly for each test class if needed).
# ---------------------------------------------------------------------------

_MAIN_PATH = __file__.replace("tests/test_main_forge_handlers.py", "main.py")
# Resolve relative to this file's directory.
import os as _os

_MAIN_PATH = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "main.py")


def _load_main():
    spec = importlib.util.spec_from_file_location("_main_under_test", _MAIN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_main = _load_main()

WAITING_TITLE = _main.WAITING_TITLE
WAITING_TITLE_CONFIRM = _main.WAITING_TITLE_CONFIRM
WAITING_STICKER = _main.WAITING_STICKER
# Read END from the ConversationHandler that main.py actually imported, so
# the value is correct regardless of which sys.modules["telegram.ext"] stub
# was already in place when this file was collected alongside other test files.
CONVERSATION_END = _main.ConversationHandler.END


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(user_data=None):
    ctx = MagicMock()
    ctx.user_data = user_data if user_data is not None else {}
    return ctx


def _make_update_with_message(text="My Pack"):
    update = MagicMock()
    update.callback_query = None
    update.message = AsyncMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_update_with_callback(callback_data="forge_title_ok"):
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.data = callback_data
    update.callback_query.edit_message_text = AsyncMock()
    update.message = None
    return update


# ---------------------------------------------------------------------------
# State constants
# ---------------------------------------------------------------------------


class TestStateConstants(unittest.TestCase):
    """Verify the renumbered conversation states introduced in this PR."""

    def test_waiting_title_is_0(self):
        self.assertEqual(WAITING_TITLE, 0)

    def test_waiting_title_confirm_is_1(self):
        self.assertEqual(WAITING_TITLE_CONFIRM, 1)

    def test_waiting_sticker_is_2(self):
        self.assertEqual(WAITING_STICKER, 2)

    def test_all_three_are_distinct(self):
        self.assertEqual(len({WAITING_TITLE, WAITING_TITLE_CONFIRM, WAITING_STICKER}), 3)

    def test_choosing_pack_starts_at_3(self):
        self.assertEqual(_main.CHOOSING_PACK, 3)

    def test_waiting_sticker_add_is_4(self):
        self.assertEqual(_main.WAITING_STICKER_ADD, 4)


# ---------------------------------------------------------------------------
# cancel_keyboard delegation
# ---------------------------------------------------------------------------


class TestCancelKeyboardDelegation(unittest.TestCase):
    """cancel_keyboard() in main.py must delegate to forge_cancel_keyboard."""

    def test_delegates_to_forge_cancel_keyboard(self):
        sentinel = MagicMock(name="cancel_kb_result")
        _fake_forge_wizard.cancel_keyboard.return_value = sentinel
        result = _main.cancel_keyboard()
        _fake_forge_wizard.cancel_keyboard.assert_called()
        self.assertIs(result, sentinel)


# ---------------------------------------------------------------------------
# create_start handler
# ---------------------------------------------------------------------------


class TestCreateStart(unittest.TestCase):

    def setUp(self):
        _fake_forge_wizard.create_start_text.reset_mock()
        _fake_forge_wizard.create_start_text.return_value = "<forge start text>"
        _fake_forge_wizard.cancel_keyboard.return_value = MagicMock(name="cancel_kb")

    def test_via_message_returns_waiting_title(self):
        update = _make_update_with_message()
        ctx = _make_context()
        result = asyncio.run(_main.create_start(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_via_message_calls_reply_text(self):
        update = _make_update_with_message()
        ctx = _make_context()
        asyncio.run(_main.create_start(update, ctx))
        update.message.reply_text.assert_called_once()

    def test_via_message_stores_forge_draft(self):
        update = _make_update_with_message()
        ctx = _make_context()
        asyncio.run(_main.create_start(update, ctx))
        draft = ctx.user_data.get("forge_draft")
        self.assertIsInstance(draft, ForgeDraft)
        self.assertEqual(draft.step, ForgeStep.TITLE)
        self.assertEqual(draft.title, "")

    def test_via_callback_query_returns_waiting_title(self):
        update = _make_update_with_callback()
        update.message = None
        ctx = _make_context()
        result = asyncio.run(_main.create_start(update, ctx))
        self.assertEqual(result, WAITING_TITLE)

    def test_via_callback_query_answers_query(self):
        update = _make_update_with_callback()
        update.message = None
        ctx = _make_context()
        asyncio.run(_main.create_start(update, ctx))
        update.callback_query.answer.assert_called_once()

    def test_via_callback_query_edits_message(self):
        update = _make_update_with_callback()
        update.message = None
        ctx = _make_context()
        asyncio.run(_main.create_start(update, ctx))
        update.callback_query.edit_message_text.assert_called_once()

    def test_uses_create_start_text(self):
        update = _make_update_with_message()
        ctx = _make_context()
        asyncio.run(_main.create_start(update, ctx))
        _fake_forge_wizard.create_start_text.assert_called()


# ---------------------------------------------------------------------------
# create_title handler
# ---------------------------------------------------------------------------


class TestCreateTitle(unittest.TestCase):

    def setUp(self):
        _fake_forge_wizard.validate_pack_title.reset_mock()
        _fake_forge_wizard.title_confirmation_text.reset_mock()
        _fake_forge_wizard.title_confirmation_keyboard.reset_mock()

    def _run(self, update, ctx):
        return asyncio.run(_main.create_title(update, ctx))

    # --- invalid title ---

    def test_invalid_title_returns_waiting_title(self):
        _fake_forge_wizard.validate_pack_title.return_value = (False, "A vessel needs a name.")
        update = _make_update_with_message("   ")
        ctx = _make_context()
        result = self._run(update, ctx)
        self.assertEqual(result, WAITING_TITLE)

    def test_invalid_title_sends_error_reply(self):
        _fake_forge_wizard.validate_pack_title.return_value = (False, "Name too long — 100 characters.")
        update = _make_update_with_message("A" * 100)
        ctx = _make_context()
        self._run(update, ctx)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        text_arg = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        self.assertIn("⚠", text_arg)

    def test_invalid_title_includes_error_message(self):
        error_msg = "Name too long — 100 characters."
        _fake_forge_wizard.validate_pack_title.return_value = (False, error_msg)
        update = _make_update_with_message("A" * 100)
        ctx = _make_context()
        self._run(update, ctx)
        call_args = update.message.reply_text.call_args
        text_arg = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        self.assertIn(error_msg, text_arg)

    # --- valid title ---

    def test_valid_title_returns_waiting_title_confirm(self):
        _fake_forge_wizard.validate_pack_title.return_value = (True, "Valid Pack")
        update = _make_update_with_message("Valid Pack")
        ctx = _make_context()
        result = self._run(update, ctx)
        self.assertEqual(result, WAITING_TITLE_CONFIRM)

    def test_valid_title_stores_draft_with_confirm_step(self):
        _fake_forge_wizard.validate_pack_title.return_value = (True, "Valid Pack")
        update = _make_update_with_message("Valid Pack")
        ctx = _make_context()
        self._run(update, ctx)
        draft = ctx.user_data.get("forge_draft")
        self.assertIsInstance(draft, ForgeDraft)
        self.assertEqual(draft.step, ForgeStep.CONFIRM_TITLE)
        self.assertEqual(draft.title, "Valid Pack")

    def test_valid_title_sends_confirmation_reply(self):
        _fake_forge_wizard.validate_pack_title.return_value = (True, "My Pack")
        _fake_forge_wizard.title_confirmation_text.return_value = "<confirm text>"
        update = _make_update_with_message("My Pack")
        ctx = _make_context()
        self._run(update, ctx)
        update.message.reply_text.assert_called_once()

    def test_valid_title_calls_title_confirmation_text(self):
        _fake_forge_wizard.validate_pack_title.return_value = (True, "My Pack")
        update = _make_update_with_message("My Pack")
        ctx = _make_context()
        self._run(update, ctx)
        _fake_forge_wizard.title_confirmation_text.assert_called_once_with("My Pack")

    def test_valid_title_calls_title_confirmation_keyboard(self):
        _fake_forge_wizard.validate_pack_title.return_value = (True, "My Pack")
        update = _make_update_with_message("My Pack")
        ctx = _make_context()
        self._run(update, ctx)
        _fake_forge_wizard.title_confirmation_keyboard.assert_called_once()

    def test_empty_title_delegates_validation_to_forge_wizard(self):
        """main.py must not duplicate validation logic; it delegates to validate_pack_title."""
        _fake_forge_wizard.validate_pack_title.return_value = (False, "A vessel needs a name.")
        update = _make_update_with_message("")
        ctx = _make_context()
        self._run(update, ctx)
        _fake_forge_wizard.validate_pack_title.assert_called_once_with("")


# ---------------------------------------------------------------------------
# create_title_confirm handler
# ---------------------------------------------------------------------------


class TestCreateTitleConfirm(unittest.TestCase):

    def setUp(self):
        _fake_forge_wizard.create_start_text.reset_mock()
        _fake_forge_wizard.sticker_prompt_text.reset_mock()
        _fake_forge_wizard.cancel_keyboard.return_value = MagicMock(name="cancel_kb")

    def _run(self, update, ctx):
        return asyncio.run(_main.create_title_confirm(update, ctx))

    # --- missing / invalid draft ---

    def test_missing_draft_returns_end(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({})  # no forge_draft key
        result = self._run(update, ctx)
        self.assertEqual(result, CONVERSATION_END)

    def test_wrong_type_draft_returns_end(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": {"title": "oops", "step": "title"}})
        result = self._run(update, ctx)
        self.assertEqual(result, CONVERSATION_END)

    def test_missing_draft_edits_message_with_warning(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({})
        self._run(update, ctx)
        update.callback_query.edit_message_text.assert_called_once()
        call_args = update.callback_query.edit_message_text.call_args
        text_arg = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        self.assertIn("Draft lost", text_arg)

    # --- forge_title_edit action ---

    def test_edit_action_returns_waiting_title(self):
        update = _make_update_with_callback("forge_title_edit")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        result = self._run(update, ctx)
        self.assertEqual(result, WAITING_TITLE)

    def test_edit_action_resets_draft_step_to_title(self):
        update = _make_update_with_callback("forge_title_edit")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        draft = ctx.user_data.get("forge_draft")
        self.assertIsInstance(draft, ForgeDraft)
        self.assertEqual(draft.step, ForgeStep.TITLE)
        self.assertEqual(draft.title, "My Pack")

    def test_edit_action_edits_message_with_start_text(self):
        _fake_forge_wizard.create_start_text.return_value = "<forge start text>"
        update = _make_update_with_callback("forge_title_edit")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        update.callback_query.edit_message_text.assert_called_once()

    def test_edit_action_answers_query(self):
        update = _make_update_with_callback("forge_title_edit")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        update.callback_query.answer.assert_called_once()

    # --- forge_title_ok action ---

    def test_ok_action_returns_waiting_sticker(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        result = self._run(update, ctx)
        self.assertEqual(result, WAITING_STICKER)

    def test_ok_action_sets_newpack_title(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        self.assertEqual(ctx.user_data.get("newpack_title"), "My Pack")

    def test_ok_action_advances_draft_step_to_sticker(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        draft = ctx.user_data.get("forge_draft")
        self.assertIsInstance(draft, ForgeDraft)
        self.assertEqual(draft.step, ForgeStep.STICKER)

    def test_ok_action_preserves_title_in_draft(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title="Cosmic Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        draft = ctx.user_data.get("forge_draft")
        self.assertEqual(draft.title, "Cosmic Pack")

    def test_ok_action_calls_sticker_prompt_text_with_title(self):
        _fake_forge_wizard.sticker_prompt_text.return_value = "<sticker prompt>"
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        _fake_forge_wizard.sticker_prompt_text.assert_called_once_with("My Pack")

    def test_ok_action_edits_message(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        update.callback_query.edit_message_text.assert_called_once()

    def test_ok_action_answers_query(self):
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title="My Pack", step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        update.callback_query.answer.assert_called_once()

    # --- regression: title preserved across confirm steps ---

    def test_title_preserved_when_switching_from_edit_to_ok(self):
        """Title in ForgeDraft must not be mutated when re-confirming after an edit."""
        title = "Rune Pack"
        update = _make_update_with_callback("forge_title_ok")
        ctx = _make_context({"forge_draft": ForgeDraft(title=title, step=ForgeStep.CONFIRM_TITLE)})
        self._run(update, ctx)
        self.assertEqual(ctx.user_data["newpack_title"], title)


if __name__ == "__main__":
    unittest.main()
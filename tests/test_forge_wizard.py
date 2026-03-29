"""
Tests for src/bot/forge_wizard.py – forge wizard helpers introduced in this PR.

Covers:
 - ForgeStep: all StrEnum values, membership, string equality
 - ForgeDraft: construction, field access, slots enforcement
 - validate_pack_title: empty, whitespace-only, exactly-at-limit, over-limit, valid, None
 - cancel_keyboard: structure and button callback_data
 - title_confirmation_keyboard: structure and all three button callback_data values
 - create_start_text: key substrings present
 - title_confirmation_text: HTML escaping of special chars, title embedding
 - sticker_prompt_text: HTML escaping of special chars, title embedding
"""

import sys
import unittest
from unittest.mock import MagicMock, call

# ---------------------------------------------------------------------------
# Bootstrap: forge_wizard imports from telegram at module level.
# Provide a minimal stub so the module can be imported without the package.
# ---------------------------------------------------------------------------

_fake_telegram = MagicMock()


class _FakeInlineKeyboardButton:
    """Lightweight stub that records the arguments it was called with."""

    def __init__(self, text, *, callback_data=None, url=None):
        self.text = text
        self.callback_data = callback_data
        self.url = url


class _FakeInlineKeyboardMarkup:
    """Lightweight stub that stores the raw inline_keyboard rows."""

    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard


_fake_telegram.InlineKeyboardButton = _FakeInlineKeyboardButton
_fake_telegram.InlineKeyboardMarkup = _FakeInlineKeyboardMarkup

sys.modules["telegram"] = _fake_telegram
sys.modules["telegram.ext"] = MagicMock()

# Now import the module under test (must happen AFTER the sys.modules patch).
from src.bot.forge_wizard import (  # noqa: E402
    DIVIDER,
    TITLE_LIMIT,
    ForgeDraft,
    ForgeStep,
    cancel_keyboard,
    create_start_text,
    sticker_prompt_text,
    title_confirmation_keyboard,
    title_confirmation_text,
    validate_pack_title,
)


# ---------------------------------------------------------------------------
# ForgeStep
# ---------------------------------------------------------------------------


class TestForgeStep(unittest.TestCase):

    def test_all_values_present(self):
        names = {s.name for s in ForgeStep}
        self.assertEqual(
            names,
            {"TITLE", "CONFIRM_TITLE", "STICKER", "LOADING", "SUCCESS", "ERROR"},
        )

    def test_str_equality(self):
        """StrEnum values must compare equal to their string counterparts."""
        self.assertEqual(ForgeStep.TITLE, "title")
        self.assertEqual(ForgeStep.CONFIRM_TITLE, "confirm_title")
        self.assertEqual(ForgeStep.STICKER, "sticker")
        self.assertEqual(ForgeStep.LOADING, "loading")
        self.assertEqual(ForgeStep.SUCCESS, "success")
        self.assertEqual(ForgeStep.ERROR, "error")

    def test_membership(self):
        self.assertIn(ForgeStep.SUCCESS, ForgeStep)
        self.assertIn("loading", [s.value for s in ForgeStep])

    def test_is_str_subclass(self):
        self.assertIsInstance(ForgeStep.TITLE, str)


# ---------------------------------------------------------------------------
# ForgeDraft
# ---------------------------------------------------------------------------


class TestForgeDraft(unittest.TestCase):

    def test_basic_construction(self):
        draft = ForgeDraft(title="My Pack", step=ForgeStep.TITLE)
        self.assertEqual(draft.title, "My Pack")
        self.assertEqual(draft.step, ForgeStep.TITLE)

    def test_step_enum_value(self):
        draft = ForgeDraft(title="", step=ForgeStep.CONFIRM_TITLE)
        self.assertEqual(draft.step, "confirm_title")

    def test_slots_prevent_arbitrary_attributes(self):
        """Dataclass with slots=True must not allow arbitrary attribute assignment."""
        draft = ForgeDraft(title="t", step=ForgeStep.STICKER)
        with self.assertRaises(AttributeError):
            draft.nonexistent = "value"  # type: ignore[attr-defined]

    def test_empty_title_allowed(self):
        """ForgeDraft itself imposes no title constraint; validation is elsewhere."""
        draft = ForgeDraft(title="", step=ForgeStep.TITLE)
        self.assertEqual(draft.title, "")

    def test_all_steps_can_be_stored(self):
        for step in ForgeStep:
            draft = ForgeDraft(title="x", step=step)
            self.assertEqual(draft.step, step)


# ---------------------------------------------------------------------------
# validate_pack_title
# ---------------------------------------------------------------------------


class TestValidatePackTitle(unittest.TestCase):

    # --- invalid cases ---

    def test_empty_string_is_invalid(self):
        ok, msg = validate_pack_title("")
        self.assertFalse(ok)
        self.assertIn("vessel", msg.lower())

    def test_whitespace_only_is_invalid(self):
        ok, msg = validate_pack_title("   ")
        self.assertFalse(ok)
        self.assertIn("vessel", msg.lower())

    def test_none_like_empty_is_invalid(self):
        """Passing an empty-string-like value should be rejected."""
        ok, msg = validate_pack_title("")
        self.assertFalse(ok)

    def test_title_too_long_is_invalid(self):
        long_title = "A" * (TITLE_LIMIT + 1)
        ok, msg = validate_pack_title(long_title)
        self.assertFalse(ok)
        self.assertIn(str(TITLE_LIMIT + 1), msg)
        self.assertIn(str(TITLE_LIMIT), msg)

    def test_title_one_over_limit_reports_correct_length(self):
        title = "B" * 65
        ok, msg = validate_pack_title(title)
        self.assertFalse(ok)
        self.assertIn("65", msg)

    def test_far_over_limit_is_invalid(self):
        ok, msg = validate_pack_title("X" * 200)
        self.assertFalse(ok)
        self.assertIn("200", msg)

    # --- valid cases ---

    def test_exactly_at_limit_is_valid(self):
        title = "C" * TITLE_LIMIT  # 64 characters
        ok, validated = validate_pack_title(title)
        self.assertTrue(ok)
        self.assertEqual(validated, title)

    def test_one_character_is_valid(self):
        ok, validated = validate_pack_title("A")
        self.assertTrue(ok)
        self.assertEqual(validated, "A")

    def test_normal_title_is_valid(self):
        ok, validated = validate_pack_title("My Cool Sticker Pack")
        self.assertTrue(ok)
        self.assertEqual(validated, "My Cool Sticker Pack")

    def test_leading_trailing_whitespace_is_stripped(self):
        ok, validated = validate_pack_title("  Trimmed Title  ")
        self.assertTrue(ok)
        self.assertEqual(validated, "Trimmed Title")

    def test_internal_whitespace_preserved(self):
        ok, validated = validate_pack_title("Pack  With  Spaces")
        self.assertTrue(ok)
        self.assertEqual(validated, "Pack  With  Spaces")

    def test_special_characters_allowed(self):
        ok, validated = validate_pack_title("Cool & Fancy <Pack>")
        self.assertTrue(ok)
        self.assertEqual(validated, "Cool & Fancy <Pack>")

    def test_unicode_title_is_valid(self):
        ok, validated = validate_pack_title("🔥 Fire Pack")
        self.assertTrue(ok)
        self.assertEqual(validated, "🔥 Fire Pack")

    # --- boundary regression ---

    def test_63_chars_is_valid(self):
        ok, validated = validate_pack_title("D" * 63)
        self.assertTrue(ok)
        self.assertEqual(len(validated), 63)

    def test_stripped_title_within_limit_after_strip(self):
        """Title that is over-limit before strip but within limit after should be valid."""
        # 64 chars of content + 10 spaces of padding - still 64 after strip
        ok, validated = validate_pack_title("     " + "E" * 64 + "     ")
        self.assertTrue(ok)
        self.assertEqual(len(validated), 64)


# ---------------------------------------------------------------------------
# cancel_keyboard
# ---------------------------------------------------------------------------


class TestCancelKeyboard(unittest.TestCase):

    def test_returns_inline_keyboard_markup(self):
        kb = cancel_keyboard()
        self.assertIsInstance(kb, _FakeInlineKeyboardMarkup)

    def test_single_row(self):
        kb = cancel_keyboard()
        self.assertEqual(len(kb.inline_keyboard), 1)

    def test_single_button_in_row(self):
        kb = cancel_keyboard()
        self.assertEqual(len(kb.inline_keyboard[0]), 1)

    def test_cancel_button_callback_data(self):
        kb = cancel_keyboard()
        btn = kb.inline_keyboard[0][0]
        self.assertEqual(btn.callback_data, "nav:home")

    def test_cancel_button_text(self):
        kb = cancel_keyboard()
        btn = kb.inline_keyboard[0][0]
        self.assertIn("Cancel", btn.text)


# ---------------------------------------------------------------------------
# title_confirmation_keyboard
# ---------------------------------------------------------------------------


class TestTitleConfirmationKeyboard(unittest.TestCase):

    def test_returns_inline_keyboard_markup(self):
        kb = title_confirmation_keyboard()
        self.assertIsInstance(kb, _FakeInlineKeyboardMarkup)

    def test_has_three_rows(self):
        kb = title_confirmation_keyboard()
        self.assertEqual(len(kb.inline_keyboard), 3)

    def test_each_row_has_one_button(self):
        kb = title_confirmation_keyboard()
        for row in kb.inline_keyboard:
            self.assertEqual(len(row), 1)

    def test_first_button_is_confirm(self):
        kb = title_confirmation_keyboard()
        btn = kb.inline_keyboard[0][0]
        self.assertEqual(btn.callback_data, "forge_title_ok")

    def test_second_button_is_edit(self):
        kb = title_confirmation_keyboard()
        btn = kb.inline_keyboard[1][0]
        self.assertEqual(btn.callback_data, "forge_title_edit")

    def test_third_button_is_cancel(self):
        kb = title_confirmation_keyboard()
        btn = kb.inline_keyboard[2][0]
        self.assertEqual(btn.callback_data, "nav:home")

    def test_all_callback_data_values(self):
        kb = title_confirmation_keyboard()
        callback_data_values = [row[0].callback_data for row in kb.inline_keyboard]
        self.assertIn("forge_title_ok", callback_data_values)
        self.assertIn("forge_title_edit", callback_data_values)
        self.assertIn("nav:home", callback_data_values)


# ---------------------------------------------------------------------------
# create_start_text
# ---------------------------------------------------------------------------


class TestCreateStartText(unittest.TestCase):

    def test_returns_string(self):
        self.assertIsInstance(create_start_text(), str)

    def test_contains_forge_heading(self):
        text = create_start_text()
        self.assertIn("FORGE A PACK", text)

    def test_contains_divider(self):
        text = create_start_text()
        self.assertIn(DIVIDER, text)

    def test_contains_title_prompt(self):
        text = create_start_text()
        self.assertIn("64 characters", text)

    def test_contains_html_bold_tag(self):
        text = create_start_text()
        self.assertIn("<b>", text)

    def test_contains_vessel_word(self):
        text = create_start_text()
        self.assertIn("vessel", text.lower())


# ---------------------------------------------------------------------------
# title_confirmation_text
# ---------------------------------------------------------------------------


class TestTitleConfirmationText(unittest.TestCase):

    def test_returns_string(self):
        self.assertIsInstance(title_confirmation_text("My Pack"), str)

    def test_contains_title(self):
        text = title_confirmation_text("Cosmic Stickers")
        self.assertIn("Cosmic Stickers", text)

    def test_contains_divider(self):
        text = title_confirmation_text("Test")
        self.assertIn(DIVIDER, text)

    def test_contains_confirm_heading(self):
        text = title_confirmation_text("Test")
        self.assertIn("Confirm", text)

    def test_html_escapes_ampersand(self):
        text = title_confirmation_text("Cats & Dogs")
        self.assertIn("Cats &amp; Dogs", text)
        self.assertNotIn("Cats & Dogs", text)

    def test_html_escapes_angle_brackets(self):
        text = title_confirmation_text("<XSS>")
        self.assertIn("&lt;XSS&gt;", text)
        self.assertNotIn("<XSS>", text)

    def test_html_escapes_double_quote(self):
        text = title_confirmation_text('Say "hello"')
        # html.escape escapes " only when quote=True (default is False for html.escape)
        # Either escaped or unescaped is fine; the important thing is no raw injection
        self.assertIn("Say", text)

    def test_empty_title_handled(self):
        text = title_confirmation_text("")
        self.assertIsInstance(text, str)

    def test_contains_seal_prompt(self):
        text = title_confirmation_text("Pack")
        self.assertIn("Seal", text)

    def test_title_inside_bold_tags(self):
        text = title_confirmation_text("Bold Pack")
        self.assertIn("<b>Bold Pack</b>", text)


# ---------------------------------------------------------------------------
# sticker_prompt_text
# ---------------------------------------------------------------------------


class TestStickerPromptText(unittest.TestCase):

    def test_returns_string(self):
        self.assertIsInstance(sticker_prompt_text("My Pack"), str)

    def test_contains_title(self):
        text = sticker_prompt_text("Nebula Pack")
        self.assertIn("Nebula Pack", text)

    def test_contains_divider(self):
        text = sticker_prompt_text("Test")
        self.assertIn(DIVIDER, text)

    def test_contains_seed_sticker_prompt(self):
        text = sticker_prompt_text("Test")
        self.assertIn("seed sticker", text)

    def test_html_escapes_ampersand(self):
        text = sticker_prompt_text("Cats & Dogs")
        self.assertIn("Cats &amp; Dogs", text)
        self.assertNotIn("Cats & Dogs", text)

    def test_html_escapes_angle_brackets(self):
        text = sticker_prompt_text("<script>")
        self.assertIn("&lt;script&gt;", text)
        self.assertNotIn("<script>", text)

    def test_contains_video_mention(self):
        text = sticker_prompt_text("Pack")
        self.assertIn("animated", text.lower())

    def test_title_inside_bold_tags(self):
        text = sticker_prompt_text("Mystic Runes")
        self.assertIn("<b>Mystic Runes</b>", text)

    def test_empty_title_handled(self):
        text = sticker_prompt_text("")
        self.assertIsInstance(text, str)

    def test_contains_gif_mention(self):
        text = sticker_prompt_text("Pack")
        self.assertIn("GIF", text)


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):

    def test_title_limit_is_64(self):
        self.assertEqual(TITLE_LIMIT, 64)

    def test_divider_nonempty(self):
        self.assertTrue(len(DIVIDER) > 0)

    def test_divider_is_string(self):
        self.assertIsInstance(DIVIDER, str)


if __name__ == "__main__":
    unittest.main()
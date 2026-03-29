"""
Tests for src/bot/forge_wizard.py – new module added in this PR.

Covers:
 - ForgeStep: all enum values, StrEnum behaviour
 - ForgeDraft: dataclass instantiation, field access, slots enforcement
 - validate_pack_title: empty input, whitespace-only, exact boundary (64),
   over-limit (65), valid title, leading/trailing whitespace trimming
 - cancel_keyboard: structure and callback_data
 - title_confirmation_keyboard: three-button structure, all callback_data values
 - create_start_text: required fragments and TITLE_LIMIT embedding
 - title_confirmation_text: title escaping, divider presence, key phrases
 - sticker_prompt_text: title escaping, divider presence, key phrases
"""

import unittest

from src.bot.forge_wizard import (
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


# ── ForgeStep ────────────────────────────────────────────────


class TestForgeStep(unittest.TestCase):
    """ForgeStep is a StrEnum – each member's value equals its string form."""

    def test_title_value(self):
        self.assertEqual(ForgeStep.TITLE, "title")

    def test_confirm_title_value(self):
        self.assertEqual(ForgeStep.CONFIRM_TITLE, "confirm_title")

    def test_sticker_value(self):
        self.assertEqual(ForgeStep.STICKER, "sticker")

    def test_loading_value(self):
        self.assertEqual(ForgeStep.LOADING, "loading")

    def test_success_value(self):
        self.assertEqual(ForgeStep.SUCCESS, "success")

    def test_error_value(self):
        self.assertEqual(ForgeStep.ERROR, "error")

    def test_all_six_members_defined(self):
        self.assertEqual(len(ForgeStep), 6)

    def test_members_are_strings(self):
        for member in ForgeStep:
            self.assertIsInstance(member, str)

    def test_string_comparison(self):
        # StrEnum members must compare equal to plain strings
        self.assertTrue(ForgeStep.SUCCESS == "success")


# ── ForgeDraft ───────────────────────────────────────────────


class TestForgeDraft(unittest.TestCase):
    """ForgeDraft is a slotted dataclass with title and step fields."""

    def test_instantiation(self):
        draft = ForgeDraft(title="My Pack", step=ForgeStep.TITLE)
        self.assertEqual(draft.title, "My Pack")
        self.assertEqual(draft.step, ForgeStep.TITLE)

    def test_title_field_accessible(self):
        draft = ForgeDraft(title="Hello", step=ForgeStep.STICKER)
        self.assertEqual(draft.title, "Hello")

    def test_step_field_accessible(self):
        draft = ForgeDraft(title="Hello", step=ForgeStep.LOADING)
        self.assertEqual(draft.step, ForgeStep.LOADING)

    def test_empty_title_allowed(self):
        draft = ForgeDraft(title="", step=ForgeStep.TITLE)
        self.assertEqual(draft.title, "")

    def test_slots_prevents_arbitrary_attributes(self):
        draft = ForgeDraft(title="X", step=ForgeStep.TITLE)
        with self.assertRaises(AttributeError):
            draft.nonexistent_field = "boom"  # type: ignore[attr-defined]

    def test_all_forge_steps_assignable(self):
        for step in ForgeStep:
            draft = ForgeDraft(title="t", step=step)
            self.assertEqual(draft.step, step)

    def test_mutable_title(self):
        draft = ForgeDraft(title="Old", step=ForgeStep.TITLE)
        draft.title = "New"
        self.assertEqual(draft.title, "New")


# ── validate_pack_title ──────────────────────────────────────


class TestValidatePackTitle(unittest.TestCase):
    """validate_pack_title returns (bool, str) – True + stripped title on success,
    False + error message on failure."""

    def test_valid_simple_title(self):
        ok, result = validate_pack_title("My Sticker Pack")
        self.assertTrue(ok)
        self.assertEqual(result, "My Sticker Pack")

    def test_strips_leading_whitespace(self):
        ok, result = validate_pack_title("   Leading")
        self.assertTrue(ok)
        self.assertEqual(result, "Leading")

    def test_strips_trailing_whitespace(self):
        ok, result = validate_pack_title("Trailing   ")
        self.assertTrue(ok)
        self.assertEqual(result, "Trailing")

    def test_strips_both_ends(self):
        ok, result = validate_pack_title("  Both Ends  ")
        self.assertTrue(ok)
        self.assertEqual(result, "Both Ends")

    def test_empty_string_is_invalid(self):
        ok, msg = validate_pack_title("")
        self.assertFalse(ok)
        self.assertIn("vessel", msg)

    def test_whitespace_only_is_invalid(self):
        ok, msg = validate_pack_title("   ")
        self.assertFalse(ok)
        self.assertIn("vessel", msg)

    def test_exactly_64_chars_is_valid(self):
        title = "A" * TITLE_LIMIT
        ok, result = validate_pack_title(title)
        self.assertTrue(ok)
        self.assertEqual(result, title)

    def test_65_chars_is_invalid(self):
        title = "A" * (TITLE_LIMIT + 1)
        ok, msg = validate_pack_title(title)
        self.assertFalse(ok)
        self.assertIn(str(TITLE_LIMIT + 1), msg)

    def test_over_limit_error_mentions_limit(self):
        title = "B" * 70
        ok, msg = validate_pack_title(title)
        self.assertFalse(ok)
        self.assertIn(str(TITLE_LIMIT), msg)

    def test_single_character_is_valid(self):
        ok, result = validate_pack_title("X")
        self.assertTrue(ok)
        self.assertEqual(result, "X")

    def test_unicode_title_valid(self):
        ok, result = validate_pack_title("Pack 🎨")
        self.assertTrue(ok)
        self.assertEqual(result, "Pack 🎨")

    def test_html_special_chars_preserved(self):
        # validate_pack_title should NOT escape – that is the caller's job
        ok, result = validate_pack_title("<b>Bold</b>")
        self.assertTrue(ok)
        self.assertEqual(result, "<b>Bold</b>")

    def test_returns_tuple_of_two(self):
        result = validate_pack_title("Title")
        self.assertEqual(len(result), 2)

    def test_valid_returns_true_as_first_element(self):
        ok, _ = validate_pack_title("Valid")
        self.assertIs(ok, True)

    def test_invalid_returns_false_as_first_element(self):
        ok, _ = validate_pack_title("")
        self.assertIs(ok, False)

    def test_boundary_63_chars_valid(self):
        title = "C" * (TITLE_LIMIT - 1)
        ok, result = validate_pack_title(title)
        self.assertTrue(ok)
        self.assertEqual(len(result), TITLE_LIMIT - 1)


# ── cancel_keyboard ──────────────────────────────────────────


class TestCancelKeyboard(unittest.TestCase):
    """cancel_keyboard returns an InlineKeyboardMarkup with a single cancel button."""

    def setUp(self):
        from telegram import InlineKeyboardMarkup
        self.InlineKeyboardMarkup = InlineKeyboardMarkup
        self.kb = cancel_keyboard()

    def test_returns_inline_keyboard_markup(self):
        self.assertIsInstance(self.kb, self.InlineKeyboardMarkup)

    def test_has_one_row(self):
        self.assertEqual(len(self.kb.inline_keyboard), 1)

    def test_row_has_one_button(self):
        self.assertEqual(len(self.kb.inline_keyboard[0]), 1)

    def test_cancel_button_callback_data(self):
        button = self.kb.inline_keyboard[0][0]
        self.assertEqual(button.callback_data, "nav:home")

    def test_cancel_button_text_contains_cancel(self):
        button = self.kb.inline_keyboard[0][0]
        self.assertIn("Cancel", button.text)


# ── title_confirmation_keyboard ──────────────────────────────


class TestTitleConfirmationKeyboard(unittest.TestCase):
    """title_confirmation_keyboard returns a three-row InlineKeyboardMarkup."""

    def setUp(self):
        from telegram import InlineKeyboardMarkup
        self.InlineKeyboardMarkup = InlineKeyboardMarkup
        self.kb = title_confirmation_keyboard()

    def test_returns_inline_keyboard_markup(self):
        self.assertIsInstance(self.kb, self.InlineKeyboardMarkup)

    def test_has_three_rows(self):
        self.assertEqual(len(self.kb.inline_keyboard), 3)

    def test_confirm_button_callback_data(self):
        confirm_btn = self.kb.inline_keyboard[0][0]
        self.assertEqual(confirm_btn.callback_data, "forge_confirm")

    def test_edit_button_callback_data(self):
        edit_btn = self.kb.inline_keyboard[1][0]
        self.assertEqual(edit_btn.callback_data, "forge_edit")

    def test_cancel_button_callback_data(self):
        cancel_btn = self.kb.inline_keyboard[2][0]
        self.assertEqual(cancel_btn.callback_data, "nav:home")

    def test_each_row_has_one_button(self):
        for row in self.kb.inline_keyboard:
            self.assertEqual(len(row), 1)

    def test_confirm_button_text_non_empty(self):
        confirm_btn = self.kb.inline_keyboard[0][0]
        self.assertTrue(confirm_btn.text.strip())

    def test_edit_button_text_non_empty(self):
        edit_btn = self.kb.inline_keyboard[1][0]
        self.assertTrue(edit_btn.text.strip())


# ── create_start_text ────────────────────────────────────────


class TestCreateStartText(unittest.TestCase):
    """create_start_text returns a consistently formatted HTML string."""

    def setUp(self):
        self.text = create_start_text()

    def test_returns_string(self):
        self.assertIsInstance(self.text, str)

    def test_contains_forge_header(self):
        self.assertIn("FORGE A PACK", self.text)

    def test_contains_divider(self):
        self.assertIn(DIVIDER, self.text)

    def test_contains_title_limit(self):
        self.assertIn(str(TITLE_LIMIT), self.text)

    def test_contains_bold_tag(self):
        self.assertIn("<b>", self.text)

    def test_contains_italic_tag(self):
        self.assertIn("<i>", self.text)

    def test_asks_for_name(self):
        self.assertIn("Name", self.text)

    def test_deterministic_output(self):
        # Called twice must produce identical output
        self.assertEqual(create_start_text(), create_start_text())


# ── title_confirmation_text ──────────────────────────────────


class TestTitleConfirmationText(unittest.TestCase):
    """title_confirmation_text embeds the (HTML-escaped) title."""

    def test_plain_title_included(self):
        text = title_confirmation_text("My Pack")
        self.assertIn("My Pack", text)

    def test_html_special_chars_escaped(self):
        text = title_confirmation_text("<script>alert(1)</script>")
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_ampersand_escaped(self):
        text = title_confirmation_text("Rock & Roll")
        self.assertIn("&amp;", text)
        self.assertNotIn(" & ", text)

    def test_contains_divider(self):
        text = title_confirmation_text("Pack")
        self.assertIn(DIVIDER, text)

    def test_contains_confirm_header(self):
        text = title_confirmation_text("Pack")
        self.assertIn("Confirm", text)

    def test_contains_instruction_phrase(self):
        text = title_confirmation_text("Pack")
        self.assertIn("Seal", text)

    def test_returns_string(self):
        self.assertIsInstance(title_confirmation_text("Pack"), str)

    def test_different_titles_produce_different_output(self):
        a = title_confirmation_text("Alpha")
        b = title_confirmation_text("Beta")
        self.assertNotEqual(a, b)

    def test_empty_string_title(self):
        # Should not raise even if caller passes empty string
        text = title_confirmation_text("")
        self.assertIsInstance(text, str)


# ── sticker_prompt_text ──────────────────────────────────────


class TestStickerPromptText(unittest.TestCase):
    """sticker_prompt_text embeds the (HTML-escaped) title in the sticker prompt."""

    def test_plain_title_included(self):
        text = sticker_prompt_text("My Pack")
        self.assertIn("My Pack", text)

    def test_html_special_chars_escaped(self):
        text = sticker_prompt_text("<Pack & Go>")
        self.assertNotIn("<Pack", text)
        self.assertIn("&lt;Pack", text)
        self.assertIn("&amp;", text)

    def test_contains_divider(self):
        text = sticker_prompt_text("Pack")
        self.assertIn(DIVIDER, text)

    def test_mentions_seed_sticker(self):
        text = sticker_prompt_text("Pack")
        self.assertIn("seed sticker", text)

    def test_mentions_image(self):
        text = sticker_prompt_text("Pack")
        self.assertIn("image", text)

    def test_mentions_video(self):
        text = sticker_prompt_text("Pack")
        self.assertIn("video", text.lower())

    def test_mentions_gif(self):
        text = sticker_prompt_text("Pack")
        self.assertIn("GIF", text)

    def test_returns_string(self):
        self.assertIsInstance(sticker_prompt_text("Pack"), str)

    def test_different_titles_produce_different_output(self):
        a = sticker_prompt_text("Alpha")
        b = sticker_prompt_text("Beta")
        self.assertNotEqual(a, b)

    def test_contains_bold_seed_sticker(self):
        text = sticker_prompt_text("Pack")
        self.assertIn("<b>seed sticker</b>", text)


# ── TITLE_LIMIT constant ─────────────────────────────────────


class TestConstants(unittest.TestCase):
    def test_title_limit_is_64(self):
        self.assertEqual(TITLE_LIMIT, 64)

    def test_divider_is_string(self):
        self.assertIsInstance(DIVIDER, str)

    def test_divider_non_empty(self):
        self.assertTrue(len(DIVIDER) > 0)


if __name__ == "__main__":
    unittest.main()
from __future__ import annotations

import html
from dataclasses import dataclass
from enum import StrEnum

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DIVIDER = "◈ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ◈"
TITLE_LIMIT = 64


class ForgeStep(StrEnum):
    TITLE = "title"
    CONFIRM_TITLE = "confirm_title"
    STICKER = "sticker"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(slots=True)
class ForgeDraft:
    title: str
    step: ForgeStep


def validate_pack_title(raw: str) -> tuple[bool, str]:
    """
    Validate and normalize a user-provided pack title.
    
    Parameters:
        raw (str): Raw user input for the pack title.
    
    Returns:
        tuple(valid, message_or_title): `valid` is `True` and `message_or_title` is the trimmed title when the input is acceptable; otherwise `valid` is `False` and `message_or_title` contains a user-facing error message explaining why the title is invalid.
    """
    title = (raw or "").strip()
    if not title:
        return False, "A vessel needs a name. Send a title to continue."
    if len(title) > TITLE_LIMIT:
        return False, f"Name too long — {len(title)} characters. Keep it under {TITLE_LIMIT}."
    return True, title


def cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Create an inline keyboard with a single "✕ Cancel" button that navigates back to home.
    
    Returns:
        InlineKeyboardMarkup: Keyboard containing one button labeled "✕ Cancel" with `callback_data` set to "nav:home".
    """
    return InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="nav:home")]])


def title_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Builds an InlineKeyboardMarkup with actions to confirm, rename, or cancel a pack title.
    
    The keyboard has three rows:
    - "✅ Seal Name" with callback_data "forge_title_ok"
    - "✏️ Rename" with callback_data "forge_title_edit"
    - "✕ Cancel" with callback_data "nav:home"
    
    Returns:
        InlineKeyboardMarkup: Markup containing the three buttons.
    """
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Seal Name", callback_data="forge_title_ok")],
            [InlineKeyboardButton("✏️ Rename", callback_data="forge_title_edit")],
            [InlineKeyboardButton("✕ Cancel", callback_data="nav:home")],
        ]
    )


def create_start_text() -> str:
    """
    Builds the localized introductory message prompting the user to name a new pack.
    
    Returns:
        start_text (str): HTML-formatted text that includes a title header, a divider, a prompt to provide a pack name, and a note that the display title may be up to 64 characters.
    """
    return (
        f"⚗️ <b>FORGE A PACK</b>\n"
        f"{DIVIDER}\n\n"
        "Name the vessel — what shall this pack be called?\n\n"
        "<i>Display title · up to 64 characters.</i>"
    )


def title_confirmation_text(title: str) -> str:
    """
    Builds the HTML-formatted confirmation message that prompts the user to confirm a vessel name.
    
    Parameters:
        title (str): The pack title to display; it will be HTML-escaped before insertion.
    
    Returns:
        str: A Telegram/HTML-formatted message containing a confirmation header, divider, the escaped title in bold, and a short instruction to seal or rename the name.
    """
    return (
        f"⚗️ <b>Confirm Vessel Name</b>\n"
        f"{DIVIDER}\n\n"
        f"<b>{html.escape(title)}</b>\n\n"
        "Seal this name, or refine it before the first sticker is bound."
    )


def sticker_prompt_text(title: str) -> str:
    """
    Builds the HTML-formatted prompt asking the user to send the seed sticker for a named pack.
    
    Parameters:
        title (str): Display title for the vessel; inserted into the message header and escaped for HTML.
    
    Returns:
        str: HTML-formatted prompt text that includes the escaped title and instructions for sending a seed sticker.
    """
    return (
        f"⚗️ <b>{html.escape(title)}</b>\n"
        f"{DIVIDER}\n\n"
        "The vessel is named. Now send the <b>seed sticker</b>.\n\n"
        "◦ Any image, photo, or GIF\n"
        "◦ Videos transmute as animated stickers\n"
        "◦ Or forward an existing sticker"
    )

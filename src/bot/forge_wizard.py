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
    Validate and normalize a candidate pack title.
    
    Strips surrounding whitespace and treats falsy inputs as empty. Enforces a non-empty title and a maximum length defined by TITLE_LIMIT; when invalid returns a user-facing error message explaining the reason.
    
    Parameters:
        raw (str): Candidate title; may be None or an empty/whitespace-only string.
    
    Returns:
        tuple[bool, str]: `(True, title)` where `title` is the stripped valid title; `(False, message)` where `message` is a user-facing error explaining why the title is invalid.
    """
    title = (raw or "").strip()
    if not title:
        return False, "A vessel needs a name. Send a title to continue."
    if len(title) > TITLE_LIMIT:
        return False, f"Name too long — {len(title)} characters. Keep it under {TITLE_LIMIT}."
    return True, title


def cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Create an inline keyboard with a single "✕ Cancel" button that navigates to the home view.
    
    Returns:
        InlineKeyboardMarkup: Inline keyboard containing one button labeled "✕ Cancel" with `callback_data="nav:home"`.
    """
    return InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="nav:home")]])


def title_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard for confirming, renaming, or cancelling the pack title.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with three rows:
            - "✅ Seal Name" (callback_data="forge_confirm")
            - "✏️ Rename" (callback_data="forge_edit")
            - "✕ Cancel" (callback_data="nav:home")
    """
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Seal Name", callback_data="menu_title_ok")],
            [InlineKeyboardButton("✏️ Rename", callback_data="menu_title_edit")],
            [InlineKeyboardButton("✕ Cancel", callback_data="nav:home")],
        ]
    )


def create_start_text() -> str:
    """
    Initial prompt text for the "Forge a Pack" wizard.
    
    Returns:
        start_text (str): The formatted message that introduces the forge flow, including the divider and a hint about the title length limit.
    """
    return (
        f"⚗️ <b>FORGE A PACK</b>\n"
        f"{DIVIDER}\n\n"
        "Name the vessel — what shall this pack be called?\n\n"
        f"<i>Display title · up to {TITLE_LIMIT} characters.</i>"
    )


def title_confirmation_text(title: str) -> str:
    """
    Construct the HTML-formatted confirmation message prompting the user to confirm a proposed pack title.
    
    Parameters:
        title (str): Proposed pack title; will be HTML-escaped before insertion.
    
    Returns:
        str: HTML string containing a bolded, escaped title and instructions to seal or refine the name.
    """
    return (
        f"⚗️ <b>Confirm Vessel Name</b>\n"
        f"{DIVIDER}\n\n"
        f"<b>{html.escape(title)}</b>\n\n"
        "Seal this name, or refine it before the first sticker is bound."
    )


def sticker_prompt_text(title: str) -> str:
    """
    Generate the sticker prompt message for the provided pack title.
    
    The returned string contains the pack title (HTML-escaped and wrapped in bold) followed by instructions describing acceptable seed sticker formats: images/photos/GIFs, videos as animated stickers, or forwarding an existing sticker.
    
    Parameters:
        title (str): The pack title to include; it will be HTML-escaped.
    
    Returns:
        str: Formatted message text containing the escaped title and sticker instructions.
    """
    return (
        f"⚗️ <b>{html.escape(title)}</b>\n"
        f"{DIVIDER}\n\n"
        "The vessel is named. Now send the <b>seed sticker</b>.\n\n"
        "◦ Any image, photo, or GIF\n"
        "◦ Videos transmute as animated stickers\n"
        "◦ Or forward an existing sticker"
    )